# SpongeBobRecomp example

- Game: SpongeBob SquarePants: Revenge of the Flying Dutchman (USA, `GSQE78`)
- Repo: <https://github.com/Spaced1127/SpongeBobRecomp>
- Build: DolRecomp static C module + ModernGekko/Dolphin runtime
- Playable core: JIT default, static module optional
- Manifest: [recomplauncher.json](recomplauncher.json)

What to notice:

- `game.kind: "iso"` with **no `check`** (GameCube is not ISO 9660); the
  Redump `dumps` size/CRC is the verified badge.
- `prepare` runs `--extract {game}` and prints `progress` lines.
- `start` runs the runner with `--module`, `--user-dir` and the setting's
  `--core static` when the player selects the static core.
- `config.new` writes `cpu_core=jit`; `always` keeps `emulation_speed=1`.
- 13 settings, including CPU core, graphics, audio and saves/logs paths.

Performance notes:

- Static module outdoors: 42.1 fps / 0.704x at 1080p MSAA 8x.
- JIT outdoors: 59.94 fps / 1.000x.
- The static module remains selectable as the faithful artifact.

Full historical notes:
[performance](../../docs/appendix/spongebob-performance.md),
[test log](../../docs/appendix/spongebob-test-log.md),
[standalone app](../../docs/appendix/spongebob-standalone-app.md),
[state](../../docs/appendix/spongebob-state.md).
