# AGENTS.md - MyRecomp project

Read the shared GameCube Static Recomp Guide first:
`https://github.com/Spaced1127/GameCube-Static-Recomp-Guide`

## Project

- Game: My Game
- Disc ID: TBD
- DOL SHA-256: TBD
- Redump: size / CRC-32
- Runtime: ModernGekko/Dolphin template
- Launcher: shared shell + per-title theme (guide docs/15)
- Playable core: JIT / static (choose after the benchmark)
- Release: TBD

## Rules

- Never add game data to Git/releases.
- Do not clean `build/` or `work/` unless explicitly asked.
- Do not edit generated C; fix the emitter/runtime and regenerate.
- Build and run a real save state before claiming a fix.
- Do not commit/tag/release without explicit approval.
- Launcher parity: same feature set as every port; change only the theme
  (names, icons, strings, manifest labels). Add features to the shell.
- Keep `STATE.md` updated with disc/build/runtime/performance/release.
- After three failed variations, change approach or ask for the missing state/log.

## Build

```powershell
cmake --build build\moderngekko --target moderngekko-run moderngekko-launcher -j 8
```

## Test

```powershell
runner --game work\game --module <module.dll> --user-dir work\test `
  --load-state <state.sav> --graphics Vulkan --audio Null `
  --automation-dir work\auto --allow-interpreter
Get-Content work\auto\status.txt
Get-Content work\test\Logs\ModernGekko.log -Tail 60
```

## Current state

See `STATE.md`.
