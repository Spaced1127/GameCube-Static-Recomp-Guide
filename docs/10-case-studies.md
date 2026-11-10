# 10 - Case studies

## SpongeBob SquarePants: Revenge of the Flying Dutchman (GSQE78)

Repository: <https://github.com/Spaced1127/SpongeBobRecomp>

### Identity

```text
Disc ID:      GSQE78
Region:       USA / NTSC-U
Redump size:  1459978240
Redump CRC32: f2facf74
DOL SHA-256:  dca4f72b57e8bf3f540e694f01cc23ef687d2b25028d974b67356e15f1c2e009
Entry point:  0x80003140
```

### Build and runtime

- ModernGekko/Dolphin template, DolRecomp C backend, Clang PGO module.
- Launcher + runner split; ISO/RVZ import, DOL hash verification, EFB access.
- Module options: loop budget 4096, max call depth 128, `x86-64-v3`, ThinLTO,
  PGO from gameplay.
- Final static build held 59-60.5 FPS in the living room and 59.9 on the title
  screen.
- `Sys/GameSettings/GSQE78.ini` sets `StaticRecompIdlePC = 0x800F5F90` for the
  frame-limiter loop.

### What went wrong and how it was fixed

1. **MSVC module was slow.** Clang `-O3` raised the living room from 27.8 to
   46.8 fps.
2. **Cache ops fell back.** The emitter used `ppc_fallback_instruction` for
   every cache op. Inline `ppc_cache_control` + continue: 49.9 fps, fallbacks
   from 33M to ~18K.
3. **Cross-chunk calls took the dispatcher.** Initializing the chunk table
   enabled direct calls; intro movies went from 0.41x to 1.00x and the living
   room from 54.6 to 59.7 fps.
4. **PGO/loop tuning** brought the static module to ~59-60 fps indoors.
5. **Outdoor scene remained CPU-bound.** Bikini Bottom outside the house:
   static 42.1 fps / 0.704x at 1080p MSAA 8x; 1x/no AA 42.8 / 0.714. JIT
   reference: 59.94 / 1.000. The static module is the artifact; JIT became the
   default playable path.
6. **Fullscreen ALT+F4 could crash or hang.** A swap-chain recreation cleared
   the image list while `IsCurrentImageValid()` still returned true;
   `VKGfx::BindBackbuffer` then wrote through a null texture (`0xC0000005`,
   write to `0x40`, fault RVA `+0x2ffd00`). A failed recreation also opened a
   modal "Warning" dialog, so the process appeared to hang. v0.1.4 creates the
   window windowed, initializes the video backend, then applies borderless
   fullscreen; it destroys the borderless window directly and validates the
   current image before every present. See
   [runtime/fullscreen](04-runtime-and-launcher.md#fullscreen-and-shutdown-windows)
   and [troubleshooting](09-troubleshooting.md#window--shutdown).

### Shipping

- `recomplauncher.json` at the top of the zip, 13 settings, CPU core choice,
  Redump dump, headless `--extract` prepare with `progress` lines.
- Frame rate clamped to 1.0 (59.94 Hz); Unlocked/150/200 removed.
- Icons embedded in both executables.
- v0.1.3 asset:
  `SpongeBobRecomp-v0.1.3-Windows-x64.zip`, 28,795,409 bytes,
  SHA-256 `80F71165773E6333F4370D14A8B3C680D4E8FEED38657C1DA078A15A6AECEE63`.
- The first v0.1.3 was replaced by a JIT-default build under the same tag; new
  installs get it, existing same-tag installs may need a reinstall. Use a new
  version for a normal update.
- v0.1.4 fixed the fullscreen ALT+F4 close with the delayed/external fullscreen
  model and swap-chain validation:
  `SpongeBobRecomp-v0.1.4-Windows-x64.zip`, 28,798,211 bytes, SHA-256
  `6F22280B185ADC580A048A7DE5B5E80A3236175BE4C3080EAF7A41A69EFAEA37`.

### Lessons

- The frame limiter can dominate the PGO profile and still not be the outdoor
  bottleneck.
- Low vs high GPU settings is the fastest CPU/GPU test.
- JIT is a legitimate playable path; do not equate "static recomp" with
  "must ship the static module for gameplay".
- Keep the static module as a selectable artifact and document the difference.

## Rocket Power: Beach Bandits (GBQE78)

Repository: <https://github.com/Spaced1127/RPBB-Static-Recomp>

### Identity

```text
Disc ID:      GBQE78
Region:       USA / NTSC-U
Redump size:  1459978240
Redump CRC32: 8be53ce8
```

### Architecture

- Playable release: ModernGekko/Dolphin **JIT core**, locked 60 FPS, DSP LLE
  audio, SDL controller input.
- Static artifact: DolRecomp C module, 545,088 instructions, 0 unknown,
  runs at 40-45 FPS.
- RecompLauncher `start.env`:

```json
"env": { "MODERNGEKKO_STATICRECOMP": "0" }
```

- `game.kind: "iso_or_folder"`, `check: { "ids": ["GBQE78"], "file":
  "sys/main.dol" }`, Redump dumps.
- `rpbb_launch.exe` handles prepare/start, including `--install` and
  `--window-mode`.

### Lessons

- The same runtime already supports both cores; selecting JIT is a config/arg
  decision, not a separate engine.
- A JIT playable release plus a static artifact is a valid, honest packaging
  strategy.
- `iso_or_folder` + `check.ids` + `check.file` is a good GameCube manifest when
  both ISO and extracted folders are supported.
- Keep the manifest and launch helper in sync; the env must be set before the
  runtime selects its CPU core.
