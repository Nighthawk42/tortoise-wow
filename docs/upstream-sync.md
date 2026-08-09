# Playerbot upstream synchronization

## Tracked line

This fork follows the playerbot integration line maintained at:

```text
remote: shyalya
url:    https://github.com/Shyalya/tortoise-wow.git
branch: playerbots-integration-gh
```

The AI/Eluna work must remain a layer on top of that line. Avoid copying the
vendor playerbot repository independently or replacing the integration branch
with a different core baseline.

## Current checkpoint

The local committed base is `90419a0fdcc67ed298ddde89cbfdb3c3b99780b2`.
At the 2026-08-09 checkpoint, `shyalya/playerbots-integration-gh` is 19 commits
ahead and the local committed history is zero commits ahead. Those commits
cover graveyard recovery, bag swaps, combat commitment, pinned bots, quest
travel, healer mana conservation, autonomous pulls, battleground capacity,
rested XP, and autonomous dungeon grouping/teleport behavior. The set also
contains the integration merge `b0c303d5`.

The commits are fetched locally but deliberately not merged into an uncommitted
runtime-port worktree. Mixing an upstream merge with the Eluna/host port before
the latter has its own reviewable commit would make conflict attribution and
rollback unnecessarily risky.

The current upstream range changes 25 files. Only two overlap the dirty local
port: `src/game/Objects/Player.h` and
`src/modules/PlayerBots/playerbot/PlayerbotAIConfig.h`. Treat those as the
expected manual-review hotspots; the rest should normally merge mechanically.

## Sync procedure

After the current port is reviewed and committed:

```powershell
git fetch shyalya playerbots-integration-gh
git rev-list --left-right --count HEAD...shyalya/playerbots-integration-gh
git log --oneline --decorate HEAD..shyalya/playerbots-integration-gh
git merge --no-ff shyalya/playerbots-integration-gh
```

Resolve conflicts in favor of neither side by default. Preserve the local host
adapters, required-Eluna build contract, reproducible Boost fallback, Windows
install layout, and config-path fix while accepting upstream player behavior.

After every sync:

1. Configure and build `mangosd` and `realmd` with playerbots and Eluna.
2. Run `git diff --check` and review all conflict resolutions.
3. Boot against a database backup and confirm Eluna event 14.
4. Confirm the configured random-bot count enters the world.
5. Exercise death/revive, quest hand-in, pull, battleground, and dungeon flows
   touched by the upstream range.
6. Record the new upstream commit in this document or the merge request.
