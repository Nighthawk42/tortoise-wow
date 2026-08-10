# C++ dialogue gateway

The playerbot module now contains the first production bridge to the Python
sidecar. It is deliberately narrow: only whispers from a real player are
eligible in this slice, and the only accepted result is `chat.text`.

## Threading and ownership

`ChatReplyAction::ChatReplyDo` builds an immutable snapshot and calls
`PlayerbotDialogueGateway::TrySubmit`. That call takes a mutex only long enough
to enforce limits and copy the snapshot into a queue. It never opens a socket,
waits for the sidecar, or parses a response.

A fixed worker pool owns HTTP, serialization, response parsing, and outcome
delivery. Valid candidates enter a second bounded queue. Each bot consumes at
most four queued candidates near the start of `PlayerbotAI::UpdateAI`, so all
game-object lookups and chat emission stay on the core-owned update thread.

Before emitting, the core checks:

- the response UUID matches the request;
- the UTF-8 JSON and candidate shape are valid;
- the candidate is no more than 255 UTF-8 bytes;
- the request deadline has not elapsed;
- the bot still has the same `PlayerbotAI` instance context;
- the bot remains in the world with a session; and
- the speaking player still has the expected GUID and name.

The core reports `emitted`, `expired`, `context_changed`, `policy_rejected`, or
`bot_unavailable` to `/v1/outcomes` on the same workers. A candidate is never
treated as conversation history merely because a provider generated it.

## Backpressure

The gateway has bounded request, outcome, and response queues. Defaults are one
pending request per bot, 64 global queued requests, two workers, an eight-second
deadline, and a five-second cooldown per bot/player pair. Rejection is immediate
and the existing deterministic playerbot behavior continues. There is no core
retry loop.

Stale cooldown entries are capped relative to queue capacity. Gateway counters
track accepted requests, queue/pending/cooldown rejections, completed and failed
requests, late responses, and dropped response/outcome jobs without recording
prompt text, response text, or credentials.

## Configuration

The generated `aiplayerbot.conf.dist` files expose:

```ini
AiPlayerbot.SidecarEnabled = 0
AiPlayerbot.SidecarEndpoint = http://127.0.0.1:8100/v1/dialogue
AiPlayerbot.SidecarServerId = turtle-dev
AiPlayerbot.SidecarServiceToken =
AiPlayerbot.SidecarRequestTimeoutMs = 8000
AiPlayerbot.SidecarQueueCapacity = 64
AiPlayerbot.SidecarMaxPendingPerBot = 1
AiPlayerbot.SidecarWorkerCount = 2
AiPlayerbot.SidecarPlayerCooldownMs = 5000
```

This initial C++ transport accepts HTTP only and is intended for loopback. A
remote deployment should terminate TLS at a local proxy until native TLS is
added. `SidecarServiceToken` authenticates the core to the sidecar; it is not an
LLM provider key. Provider credentials, persona YAML, prompt assembly, and
memory configuration remain sidecar-owned.

The core sends `server_id`, `realm_id`, and `character_guid_low`. It does not
select a persona. The sidecar resolves the roster binding, allowing thousands
of bots to share generic archetypes or use detailed handcrafted profiles
without loading those profiles into MaNGOS.

## Tests

`PLAYERBOTS_BUILD_GATEWAY_TESTS=ON` adds the standalone
`playerbot_dialogue_contract_tests` executable. It checks UUID shape, request
serialization, omission of persona IDs, response correlation, malformed JSON,
byte limits, and outcome serialization. The normal `mangosd` target compiles
and links the complete worker and world-thread integration.

## 2026-08-10 runtime deployment

Commit `4e0cc07` was built, installed, and started from the organized Windows
runtime. The sidecar loaded an explicit binding for online character GUID `2`,
`Alaura` (Troll Hunter), and materialized persona
`generated.troll.hunter.2` from the generic Troll/Hunter archetype.

The deployment checks established:

- all four launcher services were healthy;
- Eluna loaded the smoke script and received world-startup event 14;
- a live dialogue request without `persona_id` resolved Alaura's binding and
  returned a 20-byte `chat.text` candidate;
- an already-expired request returned typed `deadline_expired` failure;
- provider timeout and malformed-output tests passed;
- the production C++ response parser rejected malformed JSON, invalid UTF-8,
  a mismatched request UUID, and oversized output; and
- while the sidecar listener was deliberately absent for five seconds, the
  same `mangosd` PID remained listening, continued accumulating CPU time, and
  all nine online characters stayed online. The sidecar then returned healthy.

The probe reported `bot_unavailable` rather than falsely recording `emitted`:
no real player client was logged in during automation. A human client must log
in and whisper Alaura to complete the final world-thread emission proof.
