# Release checklist

## Artifact

- [ ] Built from documented commands, not an ad-hoc tree.
- [ ] Launcher/runner icons embedded and extracted successfully.
- [ ] `recomplauncher.json` at the top.
- [ ] Schema validation: 0 errors.
- [ ] `Sys/GameSettings/<ID>.ini` present if needed.
- [ ] `README.txt` and `PLAYERS.md` current.
- [ ] No `Game/`, ISO/RVZ/WBFS/GCM, DOL, saves or textures.
- [ ] Asset name `Name-vX.Y.Z-Windows-x64.zip`.
- [ ] SHA-256 computed.

## RecompLauncher

- [ ] `game.kind`/label/dumps correct.
- [ ] No invalid GameCube `check`.
- [ ] `prepare` headless, progress, exit 0.
- [ ] `start` program/args/env tested.
- [ ] `config` path/keys tested.
- [ ] `settings` choices tested.
- [ ] Saves/logs/actions/exit codes.
- [ ] CPU core choice (JIT/static) tested.
- [ ] Update from previous release preserves `Game/`.

## Publish

- [ ] Release notes/changelog/README match.
- [ ] Tag/commit approved by user.
- [ ] `gh release create` asset + SHA256SUMS.
- [ ] Download asset back; hash matches.
- [ ] Expanded zip: manifest/schema/icons/no game data.
- [ ] Release is latest/full (not draft/prerelease unless intended).
- [ ] Same-tag replacement documented; otherwise bump version.
