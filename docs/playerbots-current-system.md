# How the current playerbots work

## Origin and local integration

The majority of the playerbot module was brought from the
[`playerbots-integration-gh`](https://github.com/r-o-sh/tortoise-wow/tree/playerbots-integration-gh)
branch of `r-o-sh/tortoise-wow`. The vendored implementation lives under
`src/modules/PlayerBots/playerbot` and is adapted to this core through
`HostHooks.cpp` and host-side compatibility changes.

This document describes the local source tree. The upstream branch is useful
historical context, but the local implementation is the authority when the two
differ.

## Runtime ownership

There are three related levels of ownership:

| Component | Responsibility |
| --- | --- |
| `RandomPlayerbotMgr` | Server-wide population, random bot login/logout policy, and commands addressed to autonomous bots |
| `PlayerbotMgr` | Bots associated with a real-player master and commands routed from that master |
| `PlayerbotAI` | One bot's state machine, engines, strategies, command queue, and action execution |

`PlayerbotLoginMgr` performs the database-backed selection and queued login or
logout work. `PlayerbotFactory` and `RandomPlayerbotFactory` initialize or
randomize characters and their equipment, spells, talents, and progression.

The core owns all of these objects. A sidecar must never keep raw pointers,
ObjectGuids, sessions, or mutable core objects.

## Host lifecycle

`src/modules/PlayerBots/playerbot/HostHooks.cpp` is the main adapter between
this MaNGOS fork and the vendored module:

1. `Player::CreatePlayerbotAI` attaches `PlayerbotAI` to bot-controlled players.
2. Player login and logout notify `RandomPlayerbotMgr` and clean up ownership.
3. The world update drives `RandomPlayerbotMgr::UpdateAI`, including login work.
4. Each player update drives its attached `PlayerbotAI` and/or `PlayerbotMgr`.
5. Chat is routed to the appropriate manager and then to a bot's command parser.
6. Level, XP, inventory, and related host events update bot state where needed.

The calls happen on core-owned threads and under core timing constraints. This
is why an LLM or memory network request must not be added directly to a host
hook, `UpdateAI`, an action, a trigger, or an Eluna callback.

## Decision loop

`PlayerbotAI` creates a class-specific `AiObjectContext` through `AiFactory`.
The factory also creates distinct engines for combat, non-combat, dead, and
reaction states.

The strategy system is composed of:

- **values**: lazily evaluated or cached observations such as current target,
  attackers, nearby players, item counts, and travel state;
- **triggers**: conditions derived from values and game state;
- **strategies**: collections of trigger/action preferences for a role or mode;
- **multipliers**: contextual changes to action relevance;
- **actions**: the only layer that performs an attempted gameplay operation;
- **engine**: evaluates triggers, ranks candidate actions, checks usefulness and
  possibility, then executes the best eligible action.

At a high level:

```text
core tick
  -> PlayerbotAI::UpdateAI
    -> choose current engine/state
      -> update context values
      -> evaluate active strategy triggers
      -> rank candidate actions
      -> execute one eligible action
      -> schedule the next update
```

`AiObjectContext` is a named object registry. Class-specific contexts register
class actions, triggers, and strategies, while shared contexts provide generic
combat, movement, travel, RPG, economy, group, and chat behavior. This registry
is the correct place to expose a future social action that consumes an already
completed sidecar result. It is not the correct place to wait for one.

## Commands and chat

Incoming player messages pass through core chat validation first. The local
core then invokes Eluna's context-appropriate chat hook; Eluna may reject or
rewrite a message. Accepted messages continue to playerbot dispatch:

- a real player's `PlayerbotMgr` handles controlled bots;
- `RandomPlayerbotMgr` handles autonomous/random bots;
- `PlayerbotAI::HandleCommand` parses text intended for a particular bot.

The module includes an `ai chat` non-combat strategy and a legacy
`PlayerbotLLMInterface`. Configuration still describes direct provider URLs and
prompt parsing. In this branch, `PlayerbotLLMInterface::Generate` intentionally
returns no response. The direct network client is not the target architecture
because it couples the game process to provider protocols, long timeouts, and
model concurrency.

Migration rule: retain the existing chat triggers and response actions where
they are useful, but replace generation with enqueue/poll operations against a
bounded core gateway. Model-specific configuration moves to the sidecar.

## Population and persistence

Random bot policy is configured in `aiplayerbot.conf`. It covers account pools,
population limits, autologin, login cadence, level distribution, maps, teleport
policy, RPG chances, battlegrounds, LFG, and performance budgets.

`PlayerbotDbStore` and the character/world/login databases contain operational
bot data. They are not personality memory. The sidecar must use separate tables
or a separate datastore and must not write directly to gameplay tables.

## Timing and failure behavior

The existing AI is designed around short, repeated updates. A provider request
can take seconds or minutes, while a healthy world tick is measured in
milliseconds. The integration therefore uses these rules:

- publish immutable event snapshots to a bounded queue;
- perform network I/O on dedicated gateway workers;
- attach a deadline and correlation ID to every request;
- discard late responses without retrying on the world thread;
- consume a result only if the bot, session, context, and policy are still valid;
- fall back to the existing deterministic behavior or silence;
- apply rate limits per bot, channel, account, and server.

## Extension points for the first sidecar slice

The smallest useful end-to-end slice is dialogue only:

1. A validated chat or social trigger creates a `dialogue.requested` snapshot.
2. The gateway worker sends it to the sidecar.
3. The sidecar resolves persona and relevant memories, calls the configured
   provider, validates the output, and returns a short dialogue candidate.
4. The worker enqueues the candidate for the owning map/player context.
5. A normal playerbot social action consumes it and sends chat only after final
   core validation.

No v1 response may name an arbitrary strategy, action, spell, item, destination,
database query, or Lua function.

