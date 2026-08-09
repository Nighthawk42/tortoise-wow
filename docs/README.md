# AI playerbot documentation

This directory is the design and implementation guide for adding persistent,
LLM-assisted personalities to the existing playerbot system.

The first architectural rule is simple: the MaNGOS core remains authoritative.
The LLM may choose dialogue and other explicitly social output, but it does not
control combat, movement, inventory, progression, authentication, or database
state. Existing playerbot strategies continue to make those decisions.

## Documents

- [How the current playerbots work](playerbots-current-system.md)
- [Target sidecar architecture](architecture.md)
- [Sidecar API contract](sidecar-api.md)
- [YAML personality system](personality-system.md)
- [Memory system](memory-system.md)
- [Required Eluna integration](eluna-integration.md)
- [Windows build and runtime bootstrap](runtime-bootstrap.md)
- [Playerbot upstream synchronization](upstream-sync.md)
- [Implementation roadmap](roadmap.md)
- [ADR: require Eluna](adr/0001-require-eluna.md)
- [ADR: sidecar owns model and memory access](adr/0002-sidecar-boundary.md)

## Current implementation status

- `BUILD_PLAYERBOTS=ON` forces `BUILD_ELUNA=ON` during CMake configuration.
- Eluna is pinned as `src/game/LuaEngine` and compiled with its VMangos host
  adapter, which is the closest match for this Turtle WoW core's APIs.
- Lua 5.2.4 is built as an internal static dependency.
- World, map, player lifecycle, XP, and chat hooks are connected to Eluna.
- Eluna defaults to enabled, traceback enabled, and unsafe Lua methods disabled.
- The combined Eluna/playerbot core compiles, links, and installs on Windows.
- The build accepts an installed Boost 1.70+ or fetches pinned Boost 1.91.0 as
  a reproducible fallback.
- Windows installation separates generated output, runtime binaries, live
  configuration, and source; required DLLs are installed beside the servers.
- The playerbot SQL schema has been imported into the existing databases from
  a verified backup, and the Eluna load/startup smoke test passes.
- The one-account smoke roster has nine generated Classic characters; all nine
  have been verified online after a clean restart.
- The sidecar transport, custom playerbot Lua bindings, YAML loader, and memory
  adapters are intentionally later phases described in the roadmap.

## Terminology

- **core**: this MaNGOS server process and its playerbot module.
- **Eluna**: the embedded Lua engine required by this project.
- **gateway**: the bounded, asynchronous bridge between core events and the
  sidecar. It is not implemented by making HTTP calls on the world thread.
- **sidecar**: a separate application that resolves personalities, memory, and
  model providers.
- **persona**: versioned YAML profile for one simulated player; it describes
  player habits and social behavior rather than an NPC role.
- **roster binding**: the mapping from an in-game character identity to a
  persona ID.
- **memory provider**: a replaceable persistence/retrieval adapter. MemPalace is
  one possible provider, not a required dependency.
