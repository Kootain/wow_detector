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

-- 将bytes数组转换为RGB图像数据
-- @param bytes: 字节数组 (0-255的整数)
-- @param width: 图像宽度(像素块数)
-- @param height: 图像高度(像素块数)
-- @param use_crc: 是否使用CRC8校验 (默认true)
-- @return: RGB数据矩阵 [row][col] = {r, g, b}
function util.bytes_to_rgb(bytes, width, height)
    local frame = {}
    append_bytes(frame, bytes)
    
    -- 计算并添加校验和
    local checksum = util.crc8(frame)
    frame[#frame + 1] = checksum
    
    -- 计算总容量
    local total_blocks = width * height
    local total_capacity = total_blocks * 3  -- 每个块3个字节(RGB)
    
    -- 创建完整的字节数组，不足部分填充0
    local full_data = {}
    for i = 1, total_capacity do
        if i <= #frame then
            full_data[i] = util.clamp(frame[i], 0, 255)
        else
            full_data[i] = 0
        end
    end
    
    -- 转换为RGB矩阵
    local rgb_matrix = {}
    for row = 1, height do
        rgb_matrix[row] = {}
        for col = 1, width do
            local block_index = (row - 1) * width + col
            local byte_offset = (block_index - 1) * 3
            
            local r = full_data[byte_offset + 1] or 0
            local g = full_data[byte_offset + 2] or 0
            local b = full_data[byte_offset + 3] or 0
            print(r, g, b)
            
            rgb_matrix[row][col] = {r, g, b}
        end
    end
    
    return rgb_matrix
end

-- ==================== 配置 ====================
local DEFAULT_CONFIG = {
    anchorPoint = "TOPLEFT", -- 屏幕锚点位置
    offsetX = 10, offsetY = -10,   -- 锚点偏移
    blocksPerRow = 8,              -- 矩阵宽度（块数）
    blocksPerCol = 8,              -- 矩阵高度（块数）
    pixelSize = 1,                 -- 每个块的像素大小（缩放）
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
            t:SetPoint("TOPLEFT", f, "TOPLEFT", (c-1)*cfg.pixelSize, -((r-1)*cfg.pixelSize))
            t:SetSize(cfg.pixelSize, cfg.pixelSize)
            t:SetDrawLayer("BACKGROUND")
            if cfg.visibleToPlayer then
                t:SetTexture(1,1,1,1)
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

    -- 头部: [序列号][长度]
    local payload = {}
    -- 序列号：大端16位，拆成高8位和低8位
    payload[#payload+1] = bit.rshift(self.sequence, 8)
    payload[#payload+1] = bit.band(self.sequence, 0xFF)
    -- 长度：大端16位，拆成高8位和低8位
    local len = #bytes
    payload[#payload+1] = bit.rshift(len, 8)   -- 高8位
    payload[#payload+1] = bit.band(len, 0xFF)  -- 低8位
    append_bytes(payload, bytes)

    local rgb_matrix = util.bytes_to_rgb(payload, cfg.blocksPerCol, cfg.blocksPerRow)

    -- 绘制RGB矩阵到纹理
    for row = 1, cfg.blocksPerRow do
        for col = 1, cfg.blocksPerCol do
            local tex = self.textures[row] and self.textures[row][col]
            if tex and rgb_matrix[row] and rgb_matrix[row][col] then
                local rgb = rgb_matrix[row][col]
                tex:SetColorTexture(rgb[1]/255, rgb[2]/255, rgb[3]/255, 1)
            elseif tex then
                -- 如果没有数据，设置为黑色
                tex:SetColorTexture(0, 0, 0, 1)
            end
        end
    end
end

-- 测试辅助函数
function visual_transmit:SendRandomPayload(numBytes)
    local bytes = {}
    for i=1,numBytes do bytes[i] = math.random(0,255) end
    self:SendBytes(bytes)
end
