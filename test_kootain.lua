-- WoW Image Channel Addon (single-file)
-- Two modules:
-- 1) visual_transmit: draws a configurable color block matrix to encode bytes as RGB triplets.
--    - independent: does not call game state APIs; provides API visual_transmit:SendBytes(bytes)
--    - supports dynamic matrix size, pixelSize, position anchor, fps (10..120), minimal checksum
--    - provides test modes (random data, throughput benchmark, pattern)
-- 2) state_encoder: collects player state (buffs/debuffs, HP/MP, spell cooldowns, casting)
--    - serializes into bytes and calls visual_transmit:SendBytes
-- NOTE: some WoW API return positions/indices differ between Classic/Retail. Adjust indices if needed.

-- ==================== Configuration ====================
local DEFAULT_CONFIG = {
    anchorPoint = "TOPLEFT", -- where on screen to draw the matrix
    offsetX = 10, offsetY = -10,   -- offset from anchor
    blocksPerRow = 8,              -- matrix width in blocks
    blocksPerCol = 8,              -- matrix height in blocks
    pixelSize = 4,                 -- how many screen pixels per block (scale)
    visibleToPlayer = false,       -- whether the blocks are visible; set true for debugging
    fps = 30,                      -- desired frame rate for updates (10..120)
    checksumMode = "crc8",       -- "none" | "xor" | "crc8"
}

-- ==================== Utility functions ====================
local bit = bit32 or bit -- for compatibility
local function clamp(v, a, b) if v < a then return a end if v > b then return b end return v end

-- Simple CRC-8 (poly 0x07) implementation
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

-- pack integer (0..2^32-1) into n bytes (big-endian)
local function int_to_bytes(num, n)
    local out = {}
    for i=n,1,-1 do
        out[i] = bit.band(num,0xFF)
        num = bit.rshift(num,8)
    end
    return out
end

-- append bytes from source into dest
local function append_bytes(dest, src)
    for i=1,#src do dest[#dest+1] = src[i] end
end

-- ==================== Module 1: visual_transmit ====================
local visual_transmit = {}
visual_transmit.config = {}
visual_transmit.frame = nil
visual_transmit.textures = {} -- flattened [row][col] => texture
visual_transmit.sequence = 0

local function make_frame()
    local cfg = visual_transmit.config
    if visual_transmit.frame then visual_transmit.frame:Hide(); visual_transmit.frame = nil end

    local totalW = cfg.blocksPerRow * cfg.pixelSize
    local totalH = cfg.blocksPerCol * cfg.pixelSize

    local f = CreateFrame("Frame", "VI_TransmitFrame", UIParent)
    f:SetSize(totalW, totalH)
    f:SetPoint(cfg.anchorPoint, UIParent, cfg.anchorPoint, cfg.offsetX, cfg.offsetY)
    f:Show()
    visual_transmit.frame = f

    -- build textures
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
                -- nearly transparent but still renderable; alpha 1 recommended so external capture sees it
                t:SetTexture(0,0,0,0)
            end
            visual_transmit.textures[r][c] = t
        end
    end
end

function visual_transmit:Configure(usercfg)
    for k,v in pairs(DEFAULT_CONFIG) do self.config[k] = usercfg and (usercfg[k] ~= nil and usercfg[k] or v) or v end
    -- clamp fps
    self.config.fps = clamp(self.config.fps, 10, 120)
    make_frame()
    -- Set up OnUpdate ticker
    if self.ticker then self.ticker:Cancel(); self.ticker = nil end
    local interval = 1 / self.config.fps
    self.ticker = C_Timer.NewTicker(interval, function() self:Heartbeat() end)
end

-- map byte index to block row/col. Each block holds up to 3 bytes (R,G,B)
-- so blockIndex = ceil(byteIndex / 3)
local function byteindex_to_pos(cfg, byteIndex)
    local blockIndex = math.floor((byteIndex-1)/3) + 1
    local row = math.floor((blockIndex-1) / cfg.blocksPerRow) + 1
    local col = ((blockIndex-1) % cfg.blocksPerRow) + 1
    return row, col
end

-- Send raw bytes (array of integers 0..255)
function visual_transmit:SendBytes(bytes)
    -- build frame with header and checksum depending on mode
    local cfg = self.config
    self.sequence = (self.sequence + 1) % 256

    -- header: [0xAA marker][seq][len]
    local payload = {}
    payload[#payload+1] = 0xAA
    payload[#payload+1] = self.sequence
    payload[#payload+1] = #bytes
    append_bytes(payload, bytes)

    local ch = 0
    if cfg.checksumMode == "crc8" then ch = crc8(payload)
    elseif cfg.checksumMode == "xor" then ch = xor_checksum(payload)
    else ch = 0 end
    payload[#payload+1] = ch

    -- Now paint payload bytes into matrix as RGB triplets per block.
    -- Clear remaining blocks to zero to avoid stale data (helps integrity in noisy visuals)
    local totalBlocks = cfg.blocksPerRow * cfg.blocksPerCol
    local totalByteCapacity = totalBlocks * 3

    -- Build fullByte array of size totalByteCapacity
    local full = {}
    for i=1,totalByteCapacity do full[i] = 0 end
    for i=1,#payload do full[i] = payload[i] end

    -- Apply quantization/safety: clamp 0..255
    for i=1,totalByteCapacity do full[i] = clamp(full[i],0,255) end

    -- Paint
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

-- Heartbeat: for now it's empty but could be used to retransmit last frame or blink
function visual_transmit:Heartbeat()
    -- no-op default
end

-- Testing helpers
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
    C_Timer.After(durationSec, function() ticker:Cancel(); print("VI Benchmark frames:", totalFrames) end)
end

-- expose module
_G.VI_visual_transmit = visual_transmit

-- ==================== Module 2: state_encoder ====================
local state_encoder = {}
state_encoder.pollInterval = 0.1 -- seconds; we'll push to visual_transmit respecting its fps
state_encoder.lastPoll = 0
state_encoder.lastSendTime = 0
state_encoder.cachedBytes = {}

-- Helper: safe get current time in ms
local function now_ms() return math.floor(GetTime() * 1000) end

-- Collect buffs and debuffs on player
local function get_aura_info(unit, index, filter)
    -- Returns table with keys: spellId, stackCount/stacks, expirationTime, duration
    if C_UnitAuras and C_UnitAuras.GetBuffDataByIndex and filter == "HELPFUL" then
        local ok, aura = pcall(C_UnitAuras.GetBuffDataByIndex, C_UnitAuras, unit, index)
        if ok and aura and aura.spellId then
            return {
                spellID = aura.spellId,
                stacks = aura.stackCount or aura.count or 0,
                expirationTime = aura.expirationTime or 0,
                duration = aura.duration or 0,
            }
        end
    elseif C_UnitAuras and C_UnitAuras.GetAuraDataByIndex then
        local ok, aura = pcall(C_UnitAuras.GetAuraDataByIndex, C_UnitAuras, unit, index, filter)
        if ok and aura and aura.spellId then
            return {
                spellID = aura.spellId,
                stacks = aura.stackCount or aura.count or 0,
                expirationTime = aura.expirationTime or 0,
                duration = aura.duration or 0,
            }
        end
    else
        -- fallback to UnitAura (UnitBuff/UnitDebuff aliases)
        local name, icon, count, dispelType, duration, expirationTime, source, isStealable, nameplateShowPersonal, spellId = UnitAura(unit, index, filter)
        if name then
            return { spellID = spellId or 0, stacks = count or 0, expirationTime = expirationTime or 0, duration = duration or 0 }
        end
    end
    return nil
end

local function collect_buffs(unit)
    local out = {}
    -- Retail can have many buffs; iterate until no aura found. Limit to 80 for safety.
    for i=1,80 do
        local info = get_aura_info(unit, i, "HELPFUL")
        if not info then break end
        local remaining = 0
        if info.expirationTime and info.expirationTime > 0 then
            remaining = math.max(0, math.floor((info.expirationTime - GetTime())*1000))
        end
        out[#out+1] = {spellID = info.spellID or 0, stacks = info.stacks or 0, remaining_ms = remaining}
    end
    return out
end

local function collect_debuffs(unit)
    local out = {}
    for i=1,80 do
        local info = get_aura_info(unit, i, "HARMFUL")
        if not info then break end
        local remaining = 0
        if info.expirationTime and info.expirationTime > 0 then
            remaining = math.max(0, math.floor((info.expirationTime - GetTime())*1000))
        end
        out[#out+1] = {spellID = info.spellID or 0, stacks = info.stacks or 0, remaining_ms = remaining}
    end
    return out
end

-- Collect basic resources
local function collect_resources(unit)
    local health = UnitHealth(unit) or 0
    local maxHealth = UnitHealthMax(unit) or 1
    local mana = UnitPower(unit) or 0
    local maxMana = UnitPowerMax(unit) or 1
    return {hp = health, hpmax = maxHealth, mp = mana, mpmax = maxMana}
end

-- Collect spell cooldowns for a small watchlist (user can register spells by ID or name)
state_encoder.watchSpells = {} -- array of spellIDs or names
function state_encoder:RegisterWatchSpell(spell)
    self.watchSpells[#self.watchSpells+1] = spell
end

local function collect_cooldowns()
    local out = {}
    for i,spell in ipairs(state_encoder.watchSpells) do
        local start, duration, enabled = GetSpellCooldown(spell)
        local ready_in = 0
        if enabled == 1 and duration and duration > 1.5 then
            -- return remaining ms
            ready_in = math.max(0, math.floor((start + duration - GetTime()) * 1000))
        end
        out[#out+1] = {spell = spell, remaining_ms = ready_in}
    end
    return out
end

-- Collect casting/channeling info
local function collect_casting()
    local name, _, _, startTime, endTime, _, castID, notInterruptible = UnitCastingInfo("player")
    if name then
        -- startTime and endTime returned in ms
        return {type = "cast", name = name, start_ms = startTime, end_ms = endTime}
    end
    local ch_name, _, _, ch_start, ch_end = UnitChannelInfo("player")
    if ch_name then
        return {type = "channel", name = ch_name, start_ms = ch_start, end_ms = ch_end}
    end
    return nil
end

-- Serializer: custom TLV-like compact binary
-- Layout (rough):
-- [tag 1 byte][length 1 byte][payload ...]
-- tags: 0x01 = resources (hp/mp scaled), 0x02 = buffs, 0x03 = debuffs, 0x04 = cooldowns, 0x05 = cast

local function serialize_state()
    local bytes = {}
    -- resources
    local res = collect_resources("player")
    -- pack hp and mp as 2 bytes each (0..65535) scaled
    local hp_pct = math.floor( (res.hp / math.max(1,res.hpmax)) * 65535 + 0.5 )
    local mp_pct = math.floor( (res.mp / math.max(1,res.mpmax)) * 65535 + 0.5 )
    bytes[#bytes+1] = 0x01
    bytes[#bytes+1] = 4
    append_bytes(bytes, int_to_bytes(hp_pct,2))
    append_bytes(bytes, int_to_bytes(mp_pct,2))

    -- buffs: limit to first 6 buffs to save space. each buff: id(2 bytes mod 65535), stacks(1), remaining_sec(2)
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

    -- debuffs: similar
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

    -- cooldowns
    local cds = collect_cooldowns()
    local nc = math.min(6,#cds)
    bytes[#bytes+1] = 0x04
    bytes[#bytes+1] = nc * 3 + 1
    bytes[#bytes+1] = nc
    for i=1,nc do
        local c = cds[i]
        -- spell id hash: use length-limited, if it's a string we'll hash first 2 bytes
        local id_num = 0
        if type(c.spell) == "number" then id_num = c.spell % 65536 else
            for j=1, math.min(3, #c.spell) do id_num = id_num * 31 + c.spell:byte(j) end
            id_num = id_num % 65536
        end
        append_bytes(bytes, int_to_bytes(id_num,2))
        append_bytes(bytes, int_to_bytes(clamp(math.floor(c.remaining_ms/1000),0,65535),1))
    end

    -- casting
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

-- Polling loop: respect transmit fps by throttling sends
function state_encoder:OnUpdate(elapsed)
    self.lastPoll = self.lastPoll + elapsed
    if self.lastPoll < self.pollInterval then return end
    self.lastPoll = 0

    local now = GetTime()
    local vi = _G.VI_visual_transmit
    if not vi or not vi.config then return end
    local minInterval = 1 / vi.config.fps
    if (now - self.lastSendTime) < minInterval then
        return
    end

    local bytes = serialize_state()
    -- vi:SendBytes(bytes)
    self.lastSendTime = now
end

-- Initialize addon
local fMain = CreateFrame("Frame", "VI_MainFrame")
fMain.elapsed = 0
fMain:SetScript("OnUpdate", function(self, elapsed)
    state_encoder:OnUpdate(elapsed)
end)

-- Public API to configure and start
function StartVI(usercfg)
    visual_transmit.config = {}
    visual_transmit:Configure(usercfg)
    -- register some example watch spells (example; user should set to spells they care)
    state_encoder.watchSpells = {}
    -- e.g., state_encoder:RegisterWatchSpell(116) -- Fireball spell id example
    print("VI started with matrix "..visual_transmit.config.blocksPerRow.."x"..visual_transmit.config.blocksPerCol.." @"..visual_transmit.config.fps.."fps")
end

-- Utility commands for testing
SLASH_VI1 = "/vicfg"
SlashCmdList["VI"] = function(msg)
    if msg == "test" then
        visual_transmit:SendRandomPayload(32)
    elseif msg == "bench" then
        visual_transmit:Benchmark(5)
    else
        print("VI commands: /vicfg test | bench")
    end
end

-- Auto start with default config for dev convenience (comment out in production)
StartVI(nil)

-- Expose modules for external inspection
_G.VI_state_encoder = state_encoder

-- End of file
