# Release checklist

## Artifact

- [ ] Built from documented commands, not an ad-hoc tree.
- [ ] Runner rebuilt from the current runtime revision; every shipped setting
      appears in the `[video]`/`[audio]` log line.
- [ ] `Sys/GC/dsp_rom.bin` and `dsp_coef.bin` shipped next to the runner.
- [ ] Generic runner built without a disc-ID/DOL gate if it accepts any game.
- [ ] Memory-card folder created and backed up; no player save committed.
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

## Window / shutdown

- [ ] Fullscreen launch -> one ALT+F4 -> clean exit, no crash dump.
- [ ] Windowed close -> clean exit.
- [ ] F11 leave/re-enter fullscreen -> close.
- [ ] Close after loading a gameplay save.
- [ ] Fullscreen double-close.
- [ ] 10 repeated fullscreen closes: no hang, crash or dump.
- [ ] No hidden `#32770` "Warning" dialog or modal panic.
- [ ] Swap-chain image validation and failed-recreation logging present.

## Publish

- [ ] Release notes/changelog/README match.
- [ ] Tag/commit approved by user.
- [ ] `gh release create` asset + SHA256SUMS.
- [ ] Download asset back; hash matches.
- [ ] Expanded zip: manifest/schema/icons/no game data.
- [ ] Release is latest/full (not draft/prerelease unless intended).
- [ ] Same-tag replacement documented; otherwise bump version.
