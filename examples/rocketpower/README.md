# Rocket Power: Beach Bandits example

- Game: Rocket Power: Beach Bandits (USA, `GBQE78`)
- Repo: <https://github.com/Spaced1127/RPBB-Static-Recomp>
- Build: ModernGekko/Dolphin runtime; DolRecomp static C module retained as an
  artifact
- Playable release: Dolphin JIT core at 60 FPS
- Manifest: [recomplauncher.json](recomplauncher.json)

What to notice:

- `game.kind: "iso_or_folder"` with `check.ids: ["GBQE78"]` and
  `check.file: "sys/main.dol"` - a good GameCube check when both ISO and
  extracted folders are supported.
- `start.env`:

```json
"env": { "MODERNGEKKO_STATICRECOMP": "0" }
```

  This selects Dolphin's JIT core; the runner must read it before
  `SelectCPUCore()` initializes.
- `prepare` uses a launch helper (`rpbb_launch.exe`) with `--prepare`,
  `--game`, `--install`, `--user-dir`.
- `config` writes Dolphin.ini/GFX.ini/frontend config; `settings` exposes
  resolution, graphics API and window mode.
- The static module runs at 40-45 FPS; the playable release uses JIT. This is
  the same split SpongeBob uses.
