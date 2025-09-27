-- Visual Transmit Module for WoW Image Channel Addon
-- 视觉传输模块：负责将字节数据通过RGB像素矩阵进行可视化传输
-- 独立模块，不依赖游戏状态API，提供 SendBytes(bytes) 接口

local addonName, addonTable = ...
if not addonTable.visual_transmit then
    addonTable.visual_transmit = {}
end
local visual_transmit = addonTable.visual_transmit

-- 位运算库兼容性
local bit = bit32 or bit or {}
if not bit.band then
    error("No bit library available. Please ensure bit32 or bit library is loaded.")
end

-- 将源字节数组追加到目标数组
local function append_bytes(dest, src)
    for i=1,#src do dest[#dest+1] = src[i] end
end

-- 内置工具函数（从 util.lua 复制）
local util = {}

-- CRC-8校验函数 (多项式0x07)
function util.crc8(data)
    local crc = 0
    for i = 1, #data do
        crc = bit.bxor(crc, data[i])  -- XOR操作
        for j = 1, 8 do
            if bit.band(crc, 0x80) ~= 0 then
                crc = bit.band(bit.bxor(bit.lshift(crc, 1), 0x07), 0xFF)
            else
                crc = bit.band(bit.lshift(crc, 1), 0xFF)
            end
        end
    end
    return crc
end

-- XOR校验函数
function util.xor_checksum(data)
    local checksum = 0
    for i = 1, #data do
        checksum = bit.bxor(checksum, data[i])  -- XOR操作
    end
    return checksum
end

-- 限制数值范围
function util.clamp(value, min, max)
    if value < min then return min end
    if value > max then return max end
    return value
end

function visual_transmit:DrawPixelImage_PxAligned(f, img, startX, startY, blockSize)
    if not f or not img then return end
    local rows = #img
    if rows == 0 then return end
    local cols = #img[1] or 0

    local scale = f:GetEffectiveScale() or UIParent:GetEffectiveScale()

    -- 把起点对齐到物理像素（整数）
    local physStartX = math.floor(startX * scale + 0.5)
    local physStartY = math.floor(startY * scale + 0.5)

    -- 纹理池，避免重复创建
    f.__pixelPool = f.__pixelPool or {}
    local pool = f.__pixelPool
    local idx = 1

    for r = 1, rows do
        for c = 1, cols do
            local px = img[r][c]
            if px then
                -- 物理像素坐标（整数）
                local physX = physStartX + (c - 1) * blockSize
                local physY = physStartY - (r - 1) * blockSize -- TOPLEFT -> 向下是负

                -- 转回 UI 单位（精确的分母为 scale）
                local uiX = physX / scale
                local uiY = physY / scale
                local uiSize = blockSize / scale

                local t = self.textures[r][c]
                t:SetColorTexture(px[1], px[2], px[3], 1)
                if PixelUtil and PixelUtil.SetPoint and PixelUtil.SetSize then
                    PixelUtil.SetSize(t, uiSize, uiSize)
                    PixelUtil.SetPoint(t, "TOPLEFT", f, "TOPLEFT", uiX, uiY)
                else
                    t:SetSize(uiSize, uiSize)
                    t:SetPoint("TOPLEFT", f, "TOPLEFT", uiX, uiY)
                end
                t:Show()
            end
        end
    end

    -- 隐藏剩余池中多余的纹理
    while pool[idx] do
        pool[idx]:Hide()
        idx = idx + 1
    end
end


function createZeroMatrix(n, m)
    local matrix = {}  -- 外层表作为行容器
    for i = 1, n do
        matrix[i] = {}  -- 内层表作为每行的列容器
        for j = 1, m do
            matrix[i][j] = {0,0,0}  -- 初始化每个元素为 0
        end
    end
    return matrix
end


-- 将bytes数组转换为RGB图像数据
-- @param bytes: 字节数组 (0-255的整数)
-- @param width: 图像宽度(像素块数)
-- @param height: 图像高度(像素块数)
-- @param use_crc: 是否使用CRC8校验 (默认true)
-- @return: RGB数据矩阵 [row][col] = {r, g, b}
function util.bytes_to_rgb(seq_id, bytes, rows, cols)
    -- 头部: [序列号][长度]
    local payload = {}
    -- 序列号：大端16位，拆成高8位和低8位
    payload[#payload+1] = bit.rshift(seq_id, 8)
    payload[#payload+1] = bit.band(seq_id, 0xFF)
    -- 长度：大端16位，拆成高8位和低8位
    local len = #bytes
    payload[#payload+1] = bit.rshift(len, 8)   -- 高8位
    payload[#payload+1] = bit.band(len, 0xFF)  -- 低8位
    append_bytes(payload, bytes)
    
    -- 计算并添加校验和
    local checksum = util.crc8(payload)
    payload[#payload + 1] = checksum

    if #payload > (rows * cols - 4) * 3 then
        return error("Payload exceeds maximum capacity")
    end

    img = createZeroMatrix(rows, cols)
    img[1][1] = {255,255,255}
    img[1][cols] = {255,255,255}
    img[rows][1] = {255,255,255}
    img[rows][cols] = {255,255,255}
    local row = 1
    local col = 1
    for i = 1, #payload, 3 do
        if (row == 1 and col == 1) or (row == 1 and col == cols) or (row == rows and col == 1) or (row == rows and col == cols) then
            col = col + 1
        end
        if col > cols then
            row = row + 1
            col = 1
        end
        local r = payload[i] or 0
        local g = payload[i+1] or 0
        local b = payload[i+2] or 0
        img[row][col] = {r, g, b}
        print(row, col, r, g, b)
        col = col + 1
    end
    return img
end

-- ==================== 配置 ====================
local DEFAULT_CONFIG = {
    anchorPoint = "TOPLEFT", -- 屏幕锚点位置
    offsetX = 10, offsetY = -10,   -- 锚点偏移
    blocksPerRow = 16,              -- 矩阵宽度（块数）
    blocksPerCol = 16,              -- 矩阵高度（块数）
    pixelSize = 3,                 -- 每个块的像素大小（缩放）
    visibleToPlayer = false,       -- 是否对玩家可见；调试时设为true
    fps = 30,                      -- 期望帧率 (10..120)
    checksumMode = "crc8",         -- "none" | "xor" | "crc8"
}

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
    for r=1,cfg.blocksPerRow do
        visual_transmit.textures[r] = {}
        for c=1,cfg.blocksPerCol do
            local t = f:CreateTexture(nil, "BACKGROUND")
            PixelUtil.SetPoint(t, "TOPLEFT", f, "TOPLEFT", (c-1)*cfg.pixelSize, -((r-1)*cfg.pixelSize))   -- PixelUtil 会处理像素对齐
            PixelUtil.SetSize(t, cfg.pixelSize, cfg.pixelSize)
            if cfg.visibleToPlayer then
                t:SetTexture(0,0,0,1)
            else
                -- 不透明的黑色纹理，确保不被游戏内容干扰
                t:SetTexture(0,0,0,1)
            end
            visual_transmit.textures[r][c] = t
        end
    end
end

function visual_transmit:Heartbeat()
    -- 空实现，子类可以重写
end

-- 配置模块
function visual_transmit:Configure(usercfg)
    for k,v in pairs(DEFAULT_CONFIG) do 
        self.config[k] = usercfg and (usercfg[k] ~= nil and usercfg[k] or v) or v 
    end
    -- 限制fps范围
    self.config.fps = util.clamp(self.config.fps, 10, 120)
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
    self.sequence = (self.sequence + 1) % 65536
    local rgb_matrix = util.bytes_to_rgb(self.sequence, bytes, cfg.blocksPerRow, cfg.blocksPerCol)
    self:DrawPixelImage_PxAligned(self.frame, rgb_matrix, cfg.offsetX, cfg.offsetY, cfg.pixelSize)
end

-- 测试辅助函数
function visual_transmit:SendRandomPayload(n)
    local bytes = {}
    for i=1,n do bytes[i] = math.random(0,255) end
    self:SendBytes(bytes)
end


function visual_transmit:Benchmark(d)
    self:SendRandomPayload(d)
end