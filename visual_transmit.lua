-- Visual Transmit Module for WoW Image Channel Addon
-- 视觉传输模块：负责将字节数据通过RGB像素矩阵进行可视化传输
-- 独立模块，不依赖游戏状态API，提供 SendBytes(bytes) 接口

local addonName, addonTable = ...

if not addonTable.pixel_drawer then
    addonTable.pixel_drawer = {}
end
local pixel_drawer = addonTable.pixel_drawer


-- ==================== 配置 ====================
local Pixel_Default_Config = {
    anchorPoint = "TOPLEFT",
    screenResolution = {2560, 1440},
    wowScreenSize = {1366, 768},
    windowsScale = 1.0,
    blockRows = 64,
    blockCols = 64,
    offsetX = 0,
    offsetY = 0,
    pixelSize = 1,
    fps = 30
}

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

-- 限制数值范围
function util.clamp(value, min, max)
    if value < min then return min end
    if value > max then return max end
    return value
end


pixel_drawer.config = {}
pixel_drawer.factor = {}
pixel_drawer.frame = nil
pixel_drawer.textures = {}
pixel_drawer.on = true
pixel_drawer.sequence = 0

local function resize()
    local cfg = pixel_drawer.config
    pixel_drawer.factor = {
        x = cfg.wowScreenSize[1] / UIParent:GetEffectiveScale() / cfg.screenResolution[1] * cfg.windowsScale,
        y = cfg.wowScreenSize[2] / UIParent:GetEffectiveScale() / cfg.screenResolution[2] * cfg.windowsScale
    }
    local factorX = pixel_drawer.factor.x
    local factorY = pixel_drawer.factor.y
    local f = pixel_drawer.frame
    f:SetSize(cfg.blockRows * cfg.pixelSize * factorX, cfg.blockCols * cfg.pixelSize * factorY)
    f:SetPoint(cfg.anchorPoint, UIParent, cfg.anchorPoint, cfg.offsetX * factorX , cfg.offsetY * factorY)
    for r=1,cfg.blockRows do
        for c=1,cfg.blockCols do
            local t = pixel_drawer.textures[r][c]
            t:SetPoint("TOPLEFT", f, "TOPLEFT", (c-1)*cfg.pixelSize * factorX, -((r-1)*cfg.pixelSize)* factorY) 
            t:SetSize(cfg.pixelSize * factorX, cfg.pixelSize * factorY)
        end
    end
end

local function init_frame()
    print("init")
    if pixel_drawer.frame and pixel_drawer.on ~= true then
        pixel_drawer.frame:Hide()
        pixel_drawer.frame = nil
        return
    end
    local cfg = pixel_drawer.config
    local f = CreateFrame("Frame", "PixelDrawerFrame", UIParent)
    -- local factorX = pixel_drawer.factor.x
    -- local factorY = pixel_drawer.factor.y
    -- f:SetSize(cfg.blockRows, cfg.blockCols)
    -- f:SetPoint(cfg.anchorPoint, UIParent, cfg.anchorPoint, cfg.offsetX * factorX , cfg.offsetY * factorY)
    pixel_drawer.frame = f

    pixel_drawer.textures = {}
    for r=1,cfg.blockRows do
        pixel_drawer.textures[r] = {}
        for c=1,cfg.blockCols do
            local t = f:CreateTexture(nil, "BACKGROUND")
            if (r+c)%2 == 0 then
                t:SetColorTexture(1, 1, 1)
            else
                t:SetColorTexture(0, 0, 0)
            end
            pixel_drawer.textures[r][c] = t
        end
    end

    f:RegisterEvent("PLAYER_LOGIN")
    f:RegisterEvent("CVAR_UPDATE")
    f:RegisterEvent("PLAYER_ENTERING_WORLD")

    -- 统一的事件回调
    f:SetScript("OnEvent", function(self, event, arg1, ...)
        resize()
        if event == "PLAYER_LOGIN" then
            print("登录完成，缩放=", UIParent:GetEffectiveScale())
        elseif event == "CVAR_UPDATE" and arg1 == "uiScale" then
            print("uiScale 变化，新缩放=", UIParent:GetEffectiveScale())
        elseif event == "PLAYER_ENTERING_WORLD" then
            print("进入世界，更新 Frame")
        end
    end)
end


function pixel_drawer:Configure(usercfg)
    for k,v in pairs(Pixel_Default_Config) do 
        self.config[k] = usercfg and (usercfg[k] ~= nil and usercfg[k] or v) or v 
    end
    init_frame()
end

function pixel_drawer:Output(bytes)
    self.sequence = (self.sequence + 1) % 65536
    local seq_id = self.sequence
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

    if #payload > (self.config.blockRows * self.config.blockCols) * 3 then
        return error("Payload exceeds maximum capacity")
    end

    local row = 1
    local col = 1
    for i = 1, #payload, 3 do
        local r = payload[i] or 0
        local g = payload[i+1] or 0
        local b = payload[i+2] or 0
        self.textures[row][col]:SetColorTexture(r/255, g/255, b/255)
        col = col + 1
        if col > self.config.blockCols then
            row = row + 1
            col = 1
        end
    end

    for r = row, self.config.blockRows do
        for c = (r == row and col or 1), self.config.blockCols do
            self.textures[r][c]:SetColorTexture(1, 1, 1)
        end
    end
end