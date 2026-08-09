# Windows build and runtime bootstrap

This runbook reproduces the pre-sidecar milestone: build the combined
Turtle WoW core, playerbots, and Eluna; install a self-contained Windows
runtime; add the playerbot database objects; and prove the Lua and bot paths.

## Directory contract

The server root is intentionally split by responsibility:

```text
Server/
|-- archive/                 recoverable legacy runtime files
|-- bin/                     installed executables, PDBs, and required DLLs
|-- build/ai-bot/            generated CMake and compiler output
|-- config/                  live .conf files and generated .conf.dist files
|-- data/                    DBC, maps, vmaps, mmaps, and other game data
|-- database/                MariaDB distribution, data, and backups
|-- dev/                     Git source checkout
|-- logs/                    server stdout, stderr, and configured logs
|-- lua_scripts/             installed Eluna scripts
`-- tools/                   external operator tools
```

Never configure an in-source build. CMake runtime and library output is rooted
in `build/ai-bot`; `cmake --install` assembles the runnable tree in `bin` and
`config`.

## Configure, build, and install

From `Server` in PowerShell:

```powershell
cmake -S dev -B build/ai-bot -G "Visual Studio 18 2026" -A x64 `
  -DCMAKE_INSTALL_PREFIX=E:/Games/TurtleWoW/Server `
  -DBUILD_PLAYERBOTS=ON `
  -DPLAYERBOTS_FETCH_BOOST=ON `
  -DUSE_PCH=ON `
  -DACE_ROOT=D:/Dev/ace

cmake --build build/ai-bot --config RelWithDebInfo `
  --target mangosd realmd --parallel 8

cmake --install build/ai-bot --config RelWithDebInfo
```

`BUILD_PLAYERBOTS=ON` forces Eluna on. If a suitable installed Boost cannot be
found, the default fallback fetches pinned Boost 1.91.0 and links its selected
components statically. The installed executables still require `ACE.dll`,
`libmySQL.dll`, `libssl-1_1-x64.dll`, and `libcrypto-1_1-x64.dll`; CMake puts
these beside the executables in `bin`.

## Live configuration

Keep the five live files in `config`:

- `anticheat.conf`
- `mangosd.conf`
- `realmd.conf`
- `aiplayerbot.conf`
- `ahbot.conf`

Use absolute paths for `DataDir`, `LogsDir`, `Database.AutoUpdate.Path`, and
`Eluna.ScriptPath` so launching from a different working directory is safe.
On Windows the compiled `SYSCONFDIR` must end in `/`; playerbots and AH-bot use
that path to find their own configuration files. Anticheat uses the same path;
installation provides `anticheat.conf.dist`, which should be copied to the live
name and reviewed before first boot.

Keep `LogSQL = 0` for ordinary operation. Enabling it during the first cache
build records hundreds of thousands of individual inserts and can create very
large console and server logs without improving the smoke test.

For a small first smoke test, use one random-bot account and a target of five
active bots:

```ini
AiPlayerbot.Enabled = 1
AiPlayerbot.RandomBotAutologin = 1
AiPlayerbot.RandomBotLoginAtStartup = 1
AiPlayerbot.RandomBotAutoCreate = 1
AiPlayerbot.MinRandomBots = 5
AiPlayerbot.MaxRandomBots = 5
AiPlayerbot.RandomBotAccountCount = 1
AiPlayerbot.DeleteRandomBotAccounts = 0
AiPlayerbot.LLMEnabled = 0
```

One Classic account holds nine generated characters. The current selection
logic can activate the whole account even with a target of five; the validated
smoke run therefore had nine online bots. Keep the legacy LLM path explicitly
disabled until the sidecar owns provider access.

## Database initialization

Back up all four databases before applying module SQL. The initial bootstrap
used `mariadb-dump --single-transaction --routines --events` and wrote
`database/backups/pre-playerbots-20260809.sql`. Do not recreate or re-import
the base databases when an existing realm, account, or character is present.

Apply the module files to `tw_char` in this order:

1. `ai_playerbot_ahbot.sql`
2. `ai_playerbot_cache.sql`
3. `ai_playerbot_custom_strategy.sql`
4. `ai_playerbot_db_store.sql`
5. `ai_playerbot_names.sql`
6. `ai_playerbot_random_bots.sql`
7. `sql/character_updates/20260708055500_ai_playerbot_random_bots_index.sql`

Apply these to `tw_world`:

1. `ai_playerbot_indexes.sql`
2. `ai_playerbot_rpg_races.sql`
3. `ai_playerbot_texts.sql`
4. Classic enchants, named locations, travel nodes, weight scales, and zone
   levels

Check for the eight named loot-template indexes before applying the index file
to a database that may already have playerbot schema. The remaining module
files drop and recreate their own tables, so they are not upgrade migrations.

The validated initial import produced 14 character-side tables, 12 world-side
tables, 100,000 character-name rows, 1,839 travel nodes, 3,488 zone-level rows,
and 2,922 help-text rows.

## Runtime proof

The installed `lua_scripts/ai-bot-smoke.lua` prints one marker when Eluna loads
the file and another when it receives world startup event 14. Both messages
must appear in `logs/mangosd.stdout.log`:

```text
[ai-bot-smoke] Eluna loaded the smoke-test script
[ai-bot-smoke] received WORLD_EVENT_ON_STARTUP (event 14)
```

The first playerbot boot builds teleport and equipment caches before it creates
accounts. This can take several minutes and is expected to generate substantial
SQL logging. Do not interrupt that first build merely because `RNDBOT` accounts
are still absent. Completion is proven by all of the following:

- the log does not contain `AI Playerbot is Disabled`;
- an `RNDBOT%` account and generated characters exist;
- at least the configured target has active random-bot rows or login messages;
- `mangosd` remains running after the bots enter the world;
- `realmd` starts from `bin` with `config/realmd.conf`.

The 2026-08-09 validation completed in 29 minutes 49 seconds on its uncached
boot and 30 seconds on the next boot. It produced 1,332,488 equipment-cache
rows, 92,170 random-item-cache rows, and 254,082 teleport-cache rows. The
restart verified nine of nine generated characters online, both Eluna markers,
both server processes, 11 scripted Warden scans from the anticheat module, and
PID files under `logs/run` with no loose files at the server root.
