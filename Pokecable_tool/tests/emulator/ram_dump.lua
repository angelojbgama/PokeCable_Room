-- mGBA Lua script: load a save (alongside ROM), advance N frames, dump RAM,
-- then quit. Output path passed via env var POKECABLE_RAM_DUMP_PATH; gen via POKECABLE_GEN.
local frames_to_advance = 600
local frame_count = 0

local dump_path = os.getenv("POKECABLE_RAM_DUMP_PATH") or "/tmp/ramdump.bin"
local gen = tonumber(os.getenv("POKECABLE_GEN") or "1")

-- Memory addresses for party data (WRAM)
-- Gen 1: D163-D2F6 (party header + 6 mons)
-- Gen 2: DA22-DD68
-- Gen 3: 0x02024284 + 0x238 (gPlayerParty in IWRAM, RS); for Emerald 0x020244EC
local function dump_address(g)
    if g == 1 then return 0xD163, 0x194 end
    if g == 2 then return 0xDA22, 0x192 end
    -- gen 3 default to RS layout; FR/LG/Em use different — caller adjusts
    return 0x02024284, 0x258
end

local start_addr, length = dump_address(gen)

local function onFrame()
    frame_count = frame_count + 1
    if frame_count >= frames_to_advance then
        local data = {}
        for i = 0, length - 1 do
            table.insert(data, string.char(emu:read8(start_addr + i)))
        end
        local f = io.open(dump_path, "wb")
        if f then
            f:write(table.concat(data))
            f:close()
            console:log("dump written: " .. dump_path)
        else
            console:log("FAILED to open: " .. dump_path)
        end
        emu:quit()
    end
end

callbacks:add("frame", onFrame)
console:log("ram_dump.lua armed, gen=" .. tostring(gen) .. " dump=" .. dump_path)
