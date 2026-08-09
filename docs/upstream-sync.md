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

The required-Eluna runtime port was committed as `faa8851`. The 19-commit
Shyalya range ending at `2f95fbf0ee92c8c7f75c67de6960c1fe03a5f534`
was then merged as `4c198d229ef1f3872a9dacbbd3e121f15bb13f08` on
2026-08-09. The local branch is now two commits ahead of and zero commits
behind `shyalya/playerbots-integration-gh`.

That range covers graveyard recovery, bag swaps, combat commitment, pinned
bots, quest travel, healer mana conservation, autonomous pulls, battleground
capacity, rested XP, and autonomous dungeon grouping/teleport behavior. The
set also contains the integration merge `b0c303d5`.

The merge completed mechanically. The two overlapping files,
`src/game/Objects/Player.h` and
`src/modules/PlayerBots/playerbot/PlayerbotAIConfig.h`, were reviewed after the
merge. The resulting headers retain the local Eluna/config-path compatibility
and include the upstream rested-XP, pinned-bot, battleground-cap, and dungeon
configuration changes.

## Sync procedure

For the next upstream update:

```powershell
git fetch shyalya playerbots-integration-gh
git rev-list --left-right --count HEAD...shyalya/playerbots-integration-gh
git log --oneline --decorate HEAD..shyalya/playerbots-integration-gh
git merge --no-ff shyalya/playerbots-integration-gh
```

Resolve conflicts in favor of neither side by default. Preserve the local host
adapters, required-Eluna build contract, reproducible Boost fallback, Windows
install layout, and config-path fix while accepting upstream player behavior.

The 2026-08-09 merge was configured and rebuilt in `RelWithDebInfo`. Both
executables linked successfully with no build stderr. The installed server
reached the world-ready state in 28 seconds, loaded the Eluna smoke script,
received startup event 14, retained all populated playerbot caches, and brought
the configured five random bots online. `mangosd` and `realmd` remained
listening on ports 8090 and 3724 after the validation launch.

After every sync:

1. Configure and build `mangosd` and `realmd` with playerbots and Eluna.
2. Run `git diff --check` and review all conflict resolutions.
3. Boot against a database backup and confirm Eluna event 14.
4. Confirm the configured random-bot count enters the world.
5. Exercise death/revive, quest hand-in, pull, battleground, and dungeon flows
   touched by the upstream range.
6. Record the new upstream commit in this document or the merge request.
