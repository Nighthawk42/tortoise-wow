# Required Eluna integration

## Decision

Playerbots require Eluna in this branch. `BUILD_PLAYERBOTS=ON` forces
`BUILD_ELUNA=ON`, even if the latter was explicitly disabled. Eluna is also
available without playerbots for ordinary server scripting.

The project uses [Eluna](https://github.com/ElunaLuaEngine/Eluna) and its
[official API documentation](https://elunaluaengine.github.io/). The source is
pinned under `src/game/LuaEngine` at commit
`37280da4f0b92ce78320a94cbd6fe913bb5b41f5`; update the pin deliberately and
rebuild all supported configurations before accepting a newer revision.

## Why the VMangos adapter is selected

Eluna's compile-time host name does not perfectly match this fork's repository
name. Its `ELUNA_VMANGOS` compatibility path matches the local class layout,
method signatures, map handling, spell interfaces, and Vanilla expansion model
more closely than its `ELUNA_MANGOS` path. The build therefore defines:

```text
ENABLE_ELUNA
ELUNA_VMANGOS
ELUNA_EXPANSION=0
```

This is a technical compatibility choice, not a claim that the repository is
upstream VMangos.

## Build integration

- Root CMake defines `BUILD_ELUNA` and enforces it for playerbots.
- `dep/lualib` fetches and statically builds Lua 5.2.4.
- `src/game/CMakeLists.txt` compiles Eluna engine, hook, and method sources into
  the game library and links `lualib`.
- Game and server targets receive the required compile definitions and includes.
- Host compatibility methods are kept narrow and should be tested whenever the
  Eluna pin changes.

Windows configuration example:

```powershell
cmake -S . -B build -G "Visual Studio 18 2026" -A x64 `
  -DBUILD_PLAYERBOTS=ON -DUSE_PCH=ON -DACE_ROOT=D:/Dev/ace
cmake --build build --config RelWithDebInfo --target mangosd
```

The playerbot target accepts Boost 1.70+ and otherwise fetches pinned Boost
1.91.0. The selected Boost components are built statically, so Boost DLLs are
not runtime dependencies.

For a local command-line smoke test on Windows, `ACE.dll`, `libmySQL.dll`,
`libssl-1_1-x64.dll`, and `libcrypto-1_1-x64.dll` must be discoverable.
`cmake --install` copies the matching runtime DLLs beside the installed server
executables. See [Windows build and runtime bootstrap](runtime-bootstrap.md).

## Runtime lifecycle wired today

The host currently provides:

- Eluna configuration and script loading during world initialization;
- world startup, update, and shutdown events;
- per-map Lua state creation, update, and destruction;
- world-object Eluna event processors;
- map player-enter and player-leave hooks;
- player login and logout hooks;
- player XP hook;
- context-aware channel, group, guild, whisper, say, and related chat hooks.

Chat hooks execute after core validation and before playerbot command dispatch.
They may reject or rewrite a message. They must remain short and non-blocking.

## Runtime configuration

The distributed `mangosd.conf` template defaults to:

```ini
Eluna.Enabled = 1
Eluna.TraceBack = 1
Eluna.ScriptReloader = 0
Eluna.UseUnsafeMethods = 0
Eluna.UseDeprecatedMethods = 1
Eluna.ReloadCommand = 1
Eluna.ReloadSecurityLevel = 3
Eluna.ScriptPath = "lua_scripts"
Eluna.OnlyOnMaps = ""
Eluna.RequirePaths = ""
Eluna.RequireCPaths = ""
```

Keep unsafe methods off on bot-enabled servers. Lua scripts must not read model
provider secrets, open arbitrary sockets, or query the memory datastore.

## Custom playerbot Lua API

The first release should use standard Eluna hooks and C++ gateway integration.
A later, deliberately small binding can expose bot social intelligence:

```lua
local accepted, requestId = bot:RequestAIDialogue(event)
local status = bot:GetAIDialogueStatus(requestId)
```

The actual API should use typed arguments rather than arbitrary tables where
possible. It may enqueue supported social requests and inspect status. It may
not run an arbitrary action by string, make HTTP calls, access provider keys,
write gameplay databases, or block awaiting a response.

Every binding needs:

- ownership and map-thread checks;
- permission and chat-channel checks;
- bounded input lengths;
- per-bot and global rate limits;
- a non-blocking result;
- cancellation on logout/map destruction;
- tests for stale ObjectGuids and Lua reloads.

## Updating Eluna

1. Review upstream changes between the current and proposed commit.
2. Check Lua version and host adapter requirements.
3. Build Eluna with playerbots off.
4. Build playerbots, which implicitly enables Eluna.
5. Run lifecycle and chat-hook smoke tests.
6. Run a minimal Lua script on world, map, login, logout, and chat events.
7. Record the new commit and compatibility changes in the pull request.
