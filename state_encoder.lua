-- State Encoder Module for WoW Image Channel Addon
-- 游戏状态编码模块：收集玩家状态并序列化为字节数据
-- 包括buff/debuff、生命值/法力值、技能冷却、施法状态等

local addonName, addonTable = ...
if not addonTable.state_encoder then
    addonTable.state_encoder = {}
end
local state_encoder = addonTable.state_encoder

-- ==================== 配置 ====================
state_encoder.pollInterval = 0.1 -- 轮询间隔（秒）
state_encoder.lastPoll = 0
state_encoder.lastSendTime = 0
state_encoder.cachedBytes = {}
state_encoder.watchSpells = {
    "奥术冲击",
    "奥术弹幕",
    "奥术飞弹",
    "奥术涌动"
} -- 监控的技能列表
state_encoder.pixel_drawer = nil -- 视觉传输模块引用

-- ==================== 工具函数 ====================

local function string_to_bytes(s)
    local bytes = {}
    for i = 1, #s do
        table.insert(bytes, string.byte(s, i))
    end
    return bytes
end

-- json.lua - minimal JSON encoder for WoW addons
local json = {}

-- escape字符串中的特殊字符
local function escape_str(s)
    s = s:gsub('\\', '\\\\')
    s = s:gsub('"', '\\"')
    s = s:gsub('\n', '\\n')
    s = s:gsub('\r', '\\r')
    s = s:gsub('\t', '\\t')
    return '"' .. s .. '"'
end

-- 判断类型并编码
local function encode_value(v)
    local t = type(v)
    if t == "nil" then
        return "null"
    elseif t == "boolean" then
        return v and "true" or "false"
    elseif t == "number" then
        return tostring(v)
    elseif t == "string" then
        return escape_str(v)
    elseif t == "table" then
        -- 判断是数组还是对象
        local isArray = true
        local maxIndex = 0
        for k,v2 in pairs(v) do
            if type(k) ~= "number" then
                isArray = false
                break
            else
                if k > maxIndex then maxIndex = k end
            end
        end

        if isArray then
            local items = {}
            for i=1,maxIndex do
                items[#items+1] = encode_value(v[i])
            end
            return "[" .. table.concat(items, ",") .. "]"
        else
            local items = {}
            for k,v2 in pairs(v) do
                items[#items+1] = escape_str(k) .. ":" .. encode_value(v2)
            end
            return "{" .. table.concat(items, ",") .. "}"
        end
    else
        return '""'
    end
end

function json.encode(tbl)
    return encode_value(tbl)
end

local bit = bit32 or bit -- 兼容性处理

-- 获取当前时间（毫秒）
local function now_ms() 
    return math.floor(GetTime() * 1000) 
end

-- 将整数打包为字节数组
local function int_to_bytes(num, n)
    local out = {}
    for i=n,1,-1 do
        out[i] = bit.band(num,0xFF)
        num = bit.rshift(num,8)
    end
    return out
end

-- 追加字节数组
local function append_bytes(dest, src)
    for i=1,#src do dest[#dest+1] = src[i] end
end

-- 限制数值范围
local function clamp(v, a, b) 
    if v < a then return a end 
    if v > b then return b end 
    return v 
end

local UnitAura = UnitAura
if UnitAura == nil then
  --- Deprecated in 10.2.5
  UnitAura = function(unitToken, index, filter)
		local auraData = C_UnitAuras.GetAuraDataByIndex(unitToken, index, filter)
		if not auraData then
			return nil;
		end

		return auraData
	end
end


-- ==================== 光环信息获取 ====================
-- 获取光环信息（兼容不同版本的API）
local function get_aura_info(unit, index, filter)
    -- 返回包含以下键的表：spellId, stackCount/stacks, expirationTime, duration
    if C_UnitAuras and C_UnitAuras.GetAuraDataByIndex then
        local aura = C_UnitAuras.GetAuraDataByIndex(unit, index, filter)
        if aura and aura.spellId then
           
            return {
                spellID = aura.spellId,
                stacks = aura.applications or aura.count or 0,
                expirationTime = aura.expirationTime or 0,
                duration = aura.duration or 0,
                name = aura.name,
                iocn = aura.icon
            }
        end
    else
        -- 回退到UnitAura（UnitBuff/UnitDebuff别名）
        local name, icon, count, dispelType, duration, expirationTime, source, isStealable, nameplateShowPersonal, spellId = UnitAura(unit, index, filter)
        if name then
            return { 
                spellID = spellId or 0, 
                stacks = count or 0, 
                expirationTime = expirationTime or 0, 
                duration = duration or 0,
                name = name,
                iocn = aura.icon
            }
        end
    end
    return nil
end

-- 收集增益效果
local function collect_buffs(unit)
    local out = {}
    -- 正式服可能有很多buff；迭代直到找不到光环。为安全起见限制为80个
    for i=1,80 do
        local info = get_aura_info(unit, i, "HELPFUL")
        if not info then break end
        local remaining = 0
        if info.expirationTime and info.expirationTime > 0 then
            remaining = math.max(0, math.floor((info.expirationTime - GetTime())*1000))
        end
        out[#out+1] = {
            spell_id = info.spellID or 0, 
            stacks = info.stacks or 0, 
            remaining_ms = remaining,
            name = info.name,
            icon = info.iocn
        }
    end
    return out
end

-- 收集减益效果
local function collect_debuffs(unit)
    local out = {}
    for i=1,80 do
        local info = get_aura_info(unit, i, "HARMFUL")
        if not info then break end
        local remaining = 0
        if info.expirationTime and info.expirationTime > 0 then
            remaining = math.max(0, math.floor((info.expirationTime - GetTime())*1000))
        end
        out[#out+1] = {
            spell_id = info.spellID or 0, 
            stacks = info.stacks or 0,
            remaining_ms = remaining,
            name = info.name,
            icon = info.iocn
        }
    end
    return out
end

-- ==================== 资源信息收集 ====================
-- 收集基础资源（生命值、法力值等）
local function collect_resources(unit)
    local health = UnitHealth(unit) or 0
    local maxHealth = UnitHealthMax(unit) or 1
    local mana = UnitPower(unit) or 0
    local maxMana = UnitPowerMax(unit) or 1
    return {
        hp = health, 
        hpmax = maxHealth, 
        mp = mana, 
        mpmax = maxMana
    }
end

-- ==================== 技能冷却收集 ====================
-- 收集监控技能列表的冷却时间
local function collect_cooldowns()
    local out = {}
    for i,spell in ipairs(state_encoder.watchSpells) do
        local info = C_Spell.GetSpellInfo(spell)
        local cooldownInfo = C_Spell.GetSpellCooldown(info.spellID)
        local ready_in = 0
        if cooldownInfo and cooldownInfo.isEnabled and cooldownInfo.duration then
            -- 返回剩余毫秒数
            ready_in = math.max(0, math.floor((cooldownInfo.startTime + cooldownInfo.duration - GetTime()) * 1000))
        end
        out[#out+1] = {
            spell_id = info.spellID,
            name = info.name,
            icon = info.iconID,
            remaining_ms = ready_in
        }
    end
    return out
end

-- ==================== 施法信息收集 ====================
-- 收集施法/引导信息
local function collect_casting()
    local spell, _, icon, startTime, endTime, _, _, interruptible, spellId = UnitCastingInfo("player")
    if spell then
        -- startTime和endTime以毫秒返回
        return {
            type = "cast", 
            name = spell, 
            start_ms = startTime,
            end_ms = endTime,
            spell_id = spellId,
            icon = icon,
            remaining_ms = math.max(0, (endTime - GetTime()*1000)),
        }
    end
    -- local ch_name, _, _, ch_start, ch_end = UnitChannelInfo("player")
    local name, text, texture, startTime, endTime, isTradeSkill, notInterruptible, spellID, _, numStages = UnitChannelInfo("player")
    if name then
        return {
            type = "channel", 
            name = name, 
            start_ms = startTime, 
            end_ms = endTime,
            spell_id = spellID,
            icon = texture,
            remaining_ms = math.max(0, (endTime - GetTime()*1000)),
        }
    end
    return nil
end

-- ==================== 状态序列化 ====================
-- 序列化器：自定义TLV类似的紧凑二进制格式
-- 布局（大致）：
-- [标签 1字节][长度 1字节][载荷 ...]
-- 标签：0x01 = 资源(hp/mp缩放), 0x02 = buff, 0x03 = debuff, 0x04 = 冷却, 0x05 = 施法
local function serialize_state()
    local bytes = {}
    
    -- 资源
    local res = collect_resources("player")
    -- 将hp和mp打包为各2字节（0..65535）缩放
    local hp_pct = math.floor( (res.hp / math.max(1,res.hpmax)) * 65535 + 0.5 )
    local mp_pct = math.floor( (res.mp / math.max(1,res.mpmax)) * 65535 + 0.5 )
    bytes[#bytes+1] = 0x01
    bytes[#bytes+1] = 4
    append_bytes(bytes, int_to_bytes(hp_pct,2))
    append_bytes(bytes, int_to_bytes(mp_pct,2))

    -- buff：限制为前6个buff以节省空间。每个buff：id(2字节 mod 65535), 层数(1), 剩余秒数(2)
    local buffs = collect_buffs("player")
    local nb = math.min(6, #buffs)
    bytes[#bytes+1] = 0x02
    bytes[#bytes+1] = nb * 5 + 1
    bytes[#bytes+1] = nb
    for i=1,nb do
        local b = buffs[i]
        append_bytes(bytes, int_to_bytes(b.spellID % 65536,2))
        bytes[#bytes+1] = clamp(b.stacks,0,255)
        local rem_s = math.floor(b.remaining_ms / 1000)
        append_bytes(bytes, int_to_bytes(clamp(rem_s,0,65535),2))
    end

    -- debuff：类似
    local debuffs = collect_debuffs("player")
    local nd = math.min(6, #debuffs)
    bytes[#bytes+1] = 0x03
    bytes[#bytes+1] = nd * 5 + 1
    bytes[#bytes+1] = nd
    for i=1,nd do
        local b = debuffs[i]
        append_bytes(bytes, int_to_bytes(b.spellID % 65536,2))
        bytes[#bytes+1] = clamp(b.stacks,0,255)
        local rem_s = math.floor(b.remaining_ms / 1000)
        append_bytes(bytes, int_to_bytes(clamp(rem_s,0,65535),2))
    end

    -- 冷却
    local cds = collect_cooldowns()
    local nc = math.min(6,#cds)
    bytes[#bytes+1] = 0x04
    bytes[#bytes+1] = nc * 3 + 1
    bytes[#bytes+1] = nc
    for i=1,nc do
        local c = cds[i]
        -- 技能id哈希：使用长度限制，如果是字符串我们将哈希前2字节
        local id_num = 0
        if type(c.spell) == "number" then 
            id_num = c.spell % 65536 
        else
            for j=1, math.min(3, #c.spell) do 
                id_num = id_num * 31 + c.spell:byte(j) 
            end
            id_num = id_num % 65536
        end
        append_bytes(bytes, int_to_bytes(id_num,2))
        append_bytes(bytes, int_to_bytes(clamp(math.floor(c.remaining_ms/1000),0,65535),1))
    end

    -- 施法
    local cast = collect_casting()
    if cast then
        bytes[#bytes+1] = 0x05
        local name = cast.name or ""
        local dur = clamp(math.floor((cast.end_ms - cast.start_ms)/1000),0,65535)
        local namelen = math.min(12, #name)
        bytes[#bytes+1] = namelen + 2
        append_bytes(bytes, int_to_bytes(dur,2))
        for i=1,namelen do bytes[#bytes+1] = name:byte(i) end
    end

    return bytes
end

-- ==================== 状态序列化 ====================
-- JSON 格式输出
local function serialize_state_json()
    local state = {}

    -- 资源
    local res = collect_resources("player")
    state.resources = {
        hp = res.hp,
        hpmax = res.hpmax,
        mp = res.mp,
        mpmax = res.mpmax,
        hp_pct = res.hpmax > 0 and res.hp / res.hpmax or 0,
        mp_pct = res.mpmax > 0 and res.mp / res.mpmax or 0,
    }

    -- buffs
    local buffs = collect_buffs("player")
    state.buffs = buffs

    -- debuffs
    local debuffs = collect_debuffs("player")
    state.debuffs = debuffs

    -- 冷却
    local cds = collect_cooldowns()
    state.cooldowns = cds

    -- 施法
    local cast = collect_casting()
    if cast then
        state.casting = cast
    end

    return state
end


-- ==================== 公共接口 ====================
-- 设置视觉传输模块引用
function state_encoder:SetVisualTransmit(pixel_drawer_module)
    self.pixel_drawer = pixel_drawer_module
end

-- 注册监控技能
function state_encoder:RegisterWatchSpell(spell)
    self.watchSpells[#self.watchSpells+1] = spell
end

-- 清空监控技能列表
function state_encoder:ClearWatchSpells()
    self.watchSpells = {}
end

-- 轮询循环：通过限制发送来遵守传输fps
function state_encoder:OnUpdate(elapsed)
    self.lastPoll = self.lastPoll + elapsed
    if self.lastPoll < self.pollInterval then return end
    self.lastPoll = 0

    local now = GetTime()
    local vi = self.pixel_drawer
    if not vi or not vi.config then return end
    
    local minInterval = 1 / vi.config.fps
    if (now - self.lastSendTime) < minInterval then
        return
    end

    -- local bytes = serialize_state()
    -- if vi.Output then
    --     vi:Output(bytes)
    -- end
    local bytes = serialize_state_json()
    local data = json.encode(bytes)

    if vi.Output then
        vi:Output(string_to_bytes(data))
    end
    self.lastSendTime = now
end

-- 手动发送当前状态
function state_encoder:SendCurrentState()
    local bytes = serialize_state()
    if self.pixel_drawer and self.pixel_drawer.Output then
        self.pixel_drawer:Output(bytes)
    end
end

-- 模块已通过 addonTable.state_encoder 导出