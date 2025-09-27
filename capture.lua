-- WoW Image Channel Addon - Main Entry Point
-- 魔兽世界图像通道插件 - 主入口文件
-- 加载并协调两个独立模块：
-- 1) visual_transmit: 视觉传输工具模块
-- 2) state_encoder: 游戏状态采集模块

-- ==================== 模块加载 ====================
-- 获取插件目录路径
local addonName = GetAddOnMetadata("YourAddonName", "Title") or "WoWImageChannel"
local addonPath = "Interface\\AddOns\\" .. (addonName or "WoWImageChannel") .. "\\"

-- 加载视觉传输模块
local visual_transmit
do
    local chunk, err = loadfile(addonPath .. "visual_transmit.lua")
    if chunk then
        visual_transmit = chunk()
    else
        -- 回退：尝试直接require（如果支持）
        local ok, module = pcall(require, "visual_transmit")
        if ok then
            visual_transmit = module
        else
            error("Failed to load visual_transmit module: " .. (err or "unknown error"))
        end
    end
end

-- 加载状态编码模块
local state_encoder
do
    local chunk, err = loadfile(addonPath .. "state_encoder.lua")
    if chunk then
        state_encoder = chunk()
    else
        -- 回退：尝试直接require（如果支持）
        local ok, module = pcall(require, "state_encoder")
        if ok then
            state_encoder = module
        else
            error("Failed to load state_encoder module: " .. (err or "unknown error"))
        end
    end
end

-- ==================== 模块集成 ====================
-- 将视觉传输模块引用传递给状态编码模块
state_encoder:SetVisualTransmit(visual_transmit)

-- 创建主更新框架
local fMain = CreateFrame("Frame", "VI_MainFrame")
fMain.elapsed = 0
fMain:SetScript("OnUpdate", function(self, elapsed)
    state_encoder:OnUpdate(elapsed)
end)

-- ==================== 公共API ====================
-- 主要配置和启动函数
function StartVI(usercfg)
    -- 配置视觉传输模块
    visual_transmit:Configure(usercfg)
    
    -- 清空并设置默认监控技能（用户可以自定义）
    state_encoder:ClearWatchSpells()
    -- 示例：添加一些常用技能监控
    -- state_encoder:RegisterWatchSpell(116) -- 火球术示例
    -- state_encoder:RegisterWatchSpell("Fireball") -- 也可以使用技能名称
    
    print("VI started with matrix "..visual_transmit.config.blocksPerRow.."x"..visual_transmit.config.blocksPerCol.." @"..visual_transmit.config.fps.."fps")
end

-- 停止插件
function StopVI()
    if fMain then
        fMain:SetScript("OnUpdate", nil)
    end
    if visual_transmit and visual_transmit.ticker then
        visual_transmit.ticker:Cancel()
        visual_transmit.ticker = nil
    end
    if visual_transmit and visual_transmit.frame then
        visual_transmit.frame:Hide()
    end
    print("VI stopped")
end

-- 添加监控技能
function VI_AddWatchSpell(spell)
    if state_encoder then
        state_encoder:RegisterWatchSpell(spell)
        print("Added watch spell:", spell)
    end
end

-- 清空监控技能
function VI_ClearWatchSpells()
    if state_encoder then
        state_encoder:ClearWatchSpells()
        print("Cleared all watch spells")
    end
end

-- 手动发送当前状态
function VI_SendCurrentState()
    if state_encoder then
        state_encoder:SendCurrentState()
        print("Sent current state")
    end
end

-- 测试函数
function VI_Test(length)
    length = length or 32
    if visual_transmit then
        -- 生成指定长度的随机字符串
        local chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        local randomString = ""
        for i = 1, length do
            local randomIndex = math.random(1, #chars)
            randomString = randomString .. chars:sub(randomIndex, randomIndex)
        end
        
        -- 在聊天界面输出随机字符串
        print("Generated random string (" .. length .. " chars): " .. randomString)
        
        -- 将字符串转换为字节数组并发送
        local bytes = {}
        for i = 1, #randomString do
            bytes[i] = string.byte(randomString, i)
        end
        visual_transmit:SendBytes(bytes)
        print("Sent random string via visual transmit")
    end
end

-- 性能测试
function VI_Benchmark(duration)
    if visual_transmit then
        visual_transmit:Benchmark(duration or 5)
    end
end

-- ==================== 斜杠命令 ====================
SLASH_VI1 = "/vi"
SLASH_VI2 = "/vicfg"
SlashCmdList["VI"] = function(msg)
    local args = {}
    for word in msg:gmatch("%S+") do
        table.insert(args, word)
    end
    
    local cmd = args[1] and args[1]:lower() or ""
    
    if cmd == "start" then
        StartVI(nil)
    elseif cmd == "stop" then
        StopVI()
    elseif cmd == "test" then
        local length = tonumber(args[2]) or 32
        VI_Test(length)
    elseif cmd == "bench" or cmd == "benchmark" then
        local duration = tonumber(args[2]) or 5
        VI_Benchmark(duration)
    elseif cmd == "send" then
        VI_SendCurrentState()
    elseif cmd == "watch" then
        if args[2] then
            local spell = tonumber(args[2]) or args[2]
            VI_AddWatchSpell(spell)
        else
            print("Usage: /vi watch <spellID or spellName>")
        end
    elseif cmd == "clear" then
        VI_ClearWatchSpells()
    elseif cmd == "help" then
        print("VI Commands:")
        print("/vi start - Start the addon")
        print("/vi stop - Stop the addon")
        print("/vi test [length] - Send random string of specified length")
        print("/vi bench [duration] - Run benchmark")
        print("/vi send - Send current state")
        print("/vi watch <spell> - Add spell to watch list")
        print("/vi clear - Clear watch list")
        print("/vi help - Show this help")
    else
        print("VI commands: start|stop|test|bench|send|watch|clear|help")
        print("Type '/vi help' for detailed usage")
    end
end

-- ==================== 全局导出 ====================
-- 导出模块供外部访问
_G.VI_visual_transmit = visual_transmit
_G.VI_state_encoder = state_encoder
_G.VI_StartVI = StartVI
_G.VI_StopVI = StopVI

-- ==================== 自动启动 ====================
-- 开发便利性自动启动（生产环境中可注释掉）
StartVI(nil)

print("WoW Image Channel Addon loaded successfully!")
print("Use /vi help for available commands")
