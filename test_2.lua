-- 创建主框架
local buffFrame = CreateFrame("Frame", "PlayerBuffsViewerFrame", UIParent)
buffFrame:RegisterEvent("PLAYER_LOGIN")

-- 当插件加载完成时执行
buffFrame:SetScript("OnEvent", function(self, event)
    if event == "PLAYER_LOGIN" then
        CreateBuffButton()
    end
end)

-- 创建显示Buff的按钮
function CreateBuffButton()
    -- 创建按钮
    local button = CreateFrame("Button", "ShowBuffsButton", UIParent, "UIPanelButtonTemplate")
    button:SetSize(120, 30) -- 按钮大小
    button:SetPoint("CENTER", UIParent, "CENTER", 0, -200) -- 按钮位置
    button:SetText("显示玩家Buff") -- 按钮文字
    
    -- 设置按钮点击事件
    button:SetScript("OnClick", function()
        ShowAllPlayerBuffs()
    end)
    
    -- 按钮悬停效果（修复了这里的语法错误）
    button:SetHighlightTexture("Interface\\Buttons\\UI-Button-Highlight")
    button:GetHighlightTexture():SetBlendMode("ADD")
    
    -- 让按钮可见
    button:Show()
end

-- 获取并显示所有玩家的Buff
function ShowAllPlayerBuffs()
    -- 先显示当前玩家的Buff
    print("|cff00ff00当前玩家的Buff:|r")
    PrintUnitBuffs("player")
    
    -- 显示队伍成员的Buff
    local groupSize = GetNumGroupMembers()
    if groupSize > 0 then
        print("\n|cff00ff00队伍成员的Buff:|r")
        for i = 1, groupSize do
            local unit = IsInRaid() and "raid"..i or "party"..i
            if UnitExists(unit) then
                print("|cffffcc00" .. UnitName(unit) .. "的Buff:|r")
                PrintUnitBuffs(unit)
            end
        end
    end
end

-- 打印指定单位的所有Buff（使用当前版本API）
function PrintUnitBuffs(unit)
    if not UnitExists(unit) then return end
    
    local buffIndex = 1
    while true do
        -- 使用当前版本的API获取Buff信息
        local buffData = C_UnitAuras.GetBuffDataByIndex(unit, buffIndex)
        
        -- 如果没有更多Buff了，退出循环
        if not buffData then break end
        
        -- 获取Buff名称和ID
        local name = buffData.name
        local spellId = buffData.spellId
        
        -- 在聊天框显示Buff名称
        print(" - " .. name .. " (ID: " .. spellId .. ")")
        
        buffIndex = buffIndex + 1
    end
    
    -- 如果没有找到Buff
    if buffIndex == 1 then
        print(" - 没有找到Buff")
    end
end
