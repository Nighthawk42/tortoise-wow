local marker = "[ai-bot-smoke]"

PrintInfo(marker .. " Eluna loaded the smoke-test script")

local function on_world_startup(event)
    PrintInfo(marker .. " received WORLD_EVENT_ON_STARTUP (event " .. event .. ")")
end

RegisterServerEvent(14, on_world_startup)
