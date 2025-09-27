-- Visual Transmit Module for WoW Image Channel Addon
-- 视觉传输模块：负责将字节数据通过RGB像素矩阵进行可视化传输
-- 独立模块，不依赖游戏状态API，提供 SendBytes(bytes) 接口

local visual_transmit = {}

-- ==================== 配置 ====================
local DEFAULT_CONFIG = {
    anchorPoint = "TOPLEFT", -- 屏幕锚点位置
    offsetX = 10, offsetY = -10,   -- 锚点偏移
    blocksPerRow = 8,              -- 矩阵宽度（块数）
    blocksPerCol = 8,              -- 矩阵高度（块数）
    pixelSize = 4,                 -- 每个块的像素大小（缩放）
    visibleToPlayer = false,       -- 是否对玩家可见；调试时设为true
    fps = 30,                      -- 期望帧率 (10..120)
    checksumMode = "crc8",         -- "none" | "xor" | "crc8"
}

-- ==================== 工具函数 ====================
local bit = bit32 or bit -- 兼容性处理
local function clamp(v, a, b) if v < a then return a end if v > b then return b end return v end

-- 简单的CRC-8实现 (多项式 0x07)
local function crc8(bytes)
    local crc = 0
    for i=1,#bytes do
        crc = bit.bxor(crc, bytes[i])
        for j=1,8 do
            if bit.band(crc, 0x80) ~= 0 then
                crc = bit.band(bit.lshift(crc,1),0xFF)
                crc = bit.bxor(crc, 0x07)
            else
                crc = bit.band(bit.lshift(crc,1),0xFF)
            end
        end
    end
    return crc
end

local function xor_checksum(bytes)
    local x = 0
    for i=1,#bytes do x = bit.bxor(x, bytes[i]) end
    return bit.band(x,0xFF)
end

-- 将整数(0..2^32-1)打包为n字节(大端序)
local function int_to_bytes(num, n)
    local out = {}
    for i=n,1,-1 do
        out[i] = bit.band(num,0xFF)
        num = bit.rshift(num,8)
    end
    return out
end

-- 将源字节数组追加到目标数组
local function append_bytes(dest, src)
    for i=1,#src do dest[#dest+1] = src[i] end
end

-- ==================== 视觉传输模块 ====================
visual_transmit.config = {}
visual_transmit.frame = nil
visual_transmit.textures = {} -- 扁平化的 [row][col] => texture
visual_transmit.sequence = 0

-- 创建显示框架
local function make_frame()
    local cfg = visual_transmit.config
    if visual_transmit.frame then 
        visual_transmit.frame:Hide()
        visual_transmit.frame = nil 
    end

    local totalW = cfg.blocksPerRow * cfg.pixelSize
    local totalH = cfg.blocksPerCol * cfg.pixelSize

    local f = CreateFrame("Frame", "VI_TransmitFrame", UIParent)
    f:SetSize(totalW, totalH)
    f:SetPoint(cfg.anchorPoint, UIParent, cfg.anchorPoint, cfg.offsetX, cfg.offsetY)
    f:Show()
    visual_transmit.frame = f

    -- 构建纹理
    visual_transmit.textures = {}
    for r=1,cfg.blocksPerCol do
        visual_transmit.textures[r] = {}
        for c=1,cfg.blocksPerRow do
            local t = f:CreateTexture(nil, "BACKGROUND")
            t:SetPoint("TOPLEFT", f, "TOPLEFT", (c-1)*cfg.pixelSize, -((r-1)*cfg.pixelSize))
            t:SetSize(cfg.pixelSize, cfg.pixelSize)
            t:SetDrawLayer("BACKGROUND")
            if cfg.visibleToPlayer then
                t:SetTexture(1,1,1,0.9)
            else
                -- 几乎透明但仍可渲染；建议alpha为1以便外部捕获能看到
                t:SetTexture(0,0,0,0)
            end
            visual_transmit.textures[r][c] = t
        end
    end
end

-- 配置模块
function visual_transmit:Configure(usercfg)
    for k,v in pairs(DEFAULT_CONFIG) do 
        self.config[k] = usercfg and (usercfg[k] ~= nil and usercfg[k] or v) or v 
    end
    -- 限制fps范围
    self.config.fps = clamp(self.config.fps, 10, 120)
    make_frame()
    -- 设置OnUpdate定时器
    if self.ticker then 
        self.ticker:Cancel()
        self.ticker = nil 
    end
    local interval = 1 / self.config.fps
    self.ticker = C_Timer.NewTicker(interval, function() self:Heartbeat() end)
end

-- 发送原始字节数据（0..255的整数数组）
function visual_transmit:SendBytes(bytes)
    -- 根据模式构建带头部和校验和的帧
    local cfg = self.config
    self.sequence = (self.sequence + 1) % 256

    -- 头部: [0xAA标记][序列号][长度]
    local payload = {}
    payload[#payload+1] = 0xAA
    payload[#payload+1] = self.sequence
    payload[#payload+1] = #bytes
    append_bytes(payload, bytes)

    local ch = 0
    if cfg.checksumMode == "crc8" then 
        ch = crc8(payload)
    elseif cfg.checksumMode == "xor" then 
        ch = xor_checksum(payload)
    else 
        ch = 0 
    end
    payload[#payload+1] = ch

    -- 将载荷字节绘制到矩阵中，每个块作为RGB三元组
    -- 清除剩余块为零以避免陈旧数据（有助于在噪声视觉中保持完整性）
    local totalBlocks = cfg.blocksPerRow * cfg.blocksPerCol
    local totalByteCapacity = totalBlocks * 3

    -- 构建大小为totalByteCapacity的完整字节数组
    local full = {}
    for i=1,totalByteCapacity do full[i] = 0 end
    for i=1,#payload do full[i] = payload[i] end

    -- 应用量化/安全性：限制0..255
    for i=1,totalByteCapacity do full[i] = clamp(full[i],0,255) end

    -- 绘制
    for b=1,totalBlocks do
        local rByte = full[(b-1)*3 + 1] or 0
        local gByte = full[(b-1)*3 + 2] or 0
        local bByte = full[(b-1)*3 + 3] or 0
        local row = math.floor((b-1) / cfg.blocksPerRow) + 1
        local col = ((b-1) % cfg.blocksPerRow) + 1
        local tex = self.textures[row] and self.textures[row][col]
        if tex then
            tex:SetColorTexture(rByte/255, gByte/255, bByte/255, 1)
        end
    end
end

-- 心跳：目前为空，但可用于重传最后一帧或闪烁
function visual_transmit:Heartbeat()
    -- 默认无操作
end

-- 测试辅助函数
function visual_transmit:SendRandomPayload(numBytes)
    local bytes = {}
    for i=1,numBytes do bytes[i] = math.random(0,255) end
    self:SendBytes(bytes)
end

function visual_transmit:Benchmark(durationSec)
    durationSec = durationSec or 5
    local cfg = self.config
    local totalFrames = 0
    local t0 = GetTime()
    local function step()
        self:SendRandomPayload(math.min( cfg.blocksPerRow*cfg.blocksPerCol*3 - 4, 128))
        totalFrames = totalFrames + 1
    end
    local ticker = C_Timer.NewTicker(1/cfg.fps, step)
    C_Timer.After(durationSec, function() 
        ticker:Cancel()
        print("VI Benchmark frames:", totalFrames) 
    end)
end

-- 导出模块
return visual_transmit