-- WoW Image Channel Addon - Main Entry Point
-- 魔兽世界图像通道插件 - 主入口文件
-- 加载并协调两个独立模块：
-- 1) visual_transmit: 视觉传输工具模块
-- 2) state_encoder: 游戏状态采集模块

-- ==================== 模块加载 ====================
-- 获取插件参数和模块引用
local addonName, addonTable = ...
local state_encoder = addonTable.state_encoder
local pixel_drawer = addonTable.pixel_drawer


-- ==================== 模块集成 ====================
-- 将视觉传输模块引用传递给状态编码模块
state_encoder:SetVisualTransmit(pixel_drawer)

-- 创建主更新框架
local fMain = CreateFrame("Frame", "VI_MainFrame")
fMain.elapsed = 0


-- ==================== 公共API ====================
-- 主要配置和启动函数
function StartVI(usercfg)
    pixel_drawer:Configure(nil)
    pixel_drawer.on = true
    
    -- 清空并设置默认监控技能（用户可以自定义）
    -- state_encoder:ClearWatchSpells()
    fMain:SetScript("OnUpdate", function(self, elapsed)
        state_encoder:OnUpdate(elapsed)
    end)
end

-- 停止插件
function StopVI()
    if fMain then
        fMain:SetScript("OnUpdate", nil)
    end
    if pixel_drawer then
        pixel_drawer.on = false
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
function VI_Test(text)
    if pixel_drawer then
        -- 在聊天界面输出随机字符串
        print("Generated random string " .. text)
        
        -- 将字符串转换为字节数组并发送
        local bytes = {}
        for i = 1, #text do
            bytes[i] = string.byte(text, i)
        end
        pixel_drawer:Output(bytes)
        print("Sent random string via visual transmit")
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
        local text = args[2]
        VI_Test(text)
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
_G.VI_state_encoder = state_encoder
_G.VI_StartVI = StartVI
_G.VI_StopVI = StopVI

-- ==================== 自动启动 ====================
-- 开发便利性自动启动（生产环境中可注释掉）
StartVI(nil)

print("WoW Image Channel Addon loaded successfully!")
print("Use /vi help for available commands")
