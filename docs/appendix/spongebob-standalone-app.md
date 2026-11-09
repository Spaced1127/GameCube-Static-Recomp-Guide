# Standalone PC application

Updated: 2026-11-08

## Package

The shipped folder contains **no game data**:

| File | Purpose |
|---|---|
| `SpongeBobRecomp.exe` | Launcher: import, settings, folder picker, Play |
| `SpongeBobRecompRunner.exe` | Runtime / game process |
| `gGSQE78_recomp.dll` | Recompiled game code (no textures, audio, levels or disc data) |
| `Sys/` | Dolphin runtime data (shaders, GameSettings, controller templates) |
| `README.txt`, `PLAYERS.md` | Instructions and controls |
| `LICENSES/` | Third-party licenses |

The user supplies their own `GSQE78` GameCube disc image. The app validates the
disc ID and the retail DOL SHA-256 before extracting or launching.

## Import

Both formats were tested end-to-end with the packaged launcher:

```powershell
SpongeBobRecomp.exe --extract <game.iso>
SpongeBobRecomp.exe --extract <game.rvz>
```

Both create `Game/` with `sys/` and `files/`. The extracted
`sys/main.dol` is byte-identical to the retail DOL in both cases
(SHA-256 `dca4f72b...e009`).

The GUI exposes:

- **Browse for ISO / WBFS / RVZ** and **Extract and Play** (Dolphin DiscIO;
  RVZ is handled natively).
- **Browse for extracted game folder**, for a folder the user extracted
  elsewhere.
- **Play**, plus netplay host/join (kept from the runtime).

An existing extraction is reused; a new extraction is staged and published
atomically. Failures leave the previous install untouched.

## Settings

The launcher is a graphical shell with an animated underwater backdrop and five
pages: PLAY, GRAPHICS, PERFORMANCE, AUDIO and CONTROLLER. Settings persist in
config.ini and are applied by the runner.


- Graphics backend: Vulkan / OpenGL
- Internal resolution: 1x through 12x (640x528 up to 7680x4320)
- MSAA: off / 2x / 4x / 8x, SSAA
- Anisotropic filtering: 1x / 2x / 4x / 8x / 16x
- VSync
- Aspect ratio: auto / 16:9 / 4:3 / stretch, widescreen hack
- Emulation speed: native 100% / 150% / 200% / unlocked
- **2D compatibility (EFB access)**, default on
- Show FPS in the window title
- Audio: mute all audio and master volume 0-100%
- Unlock frame rate (removes the 60 fps cap)
- Controller profile, fullscreen, netplay

`--play` runs the same launch path as the Play button. `--set key=value` applies one
setting through the same validating parser the settings panel uses, then writes
`config.ini`; an invalid value is rejected and the file is left untouched. Both are
used for automated end-to-end testing.

## The 2D / EFB fix

The legal and title screens are TGA bitmaps composited through the engine's 2D
path. With Dolphin's default EFB optimizations they rendered black, even with
the JIT reference (so not a recompiler bug).

The fix is accurate EFB reads:

- `GFX_HACK_EFB_ACCESS_ENABLE = true` (shipped)

The slow EFB-completion settings (`GFX_HACK_SKIP_EFB_COPY_TO_RAM = false`,
`GFX_HACK_DEFER_EFB_COPIES = false`) also fix the screens but cost 3-4 fps in
3D and are **not** shipped; `SB_EFB_FULL=1` turns them on for diagnosis.

The launcher exposes the shipped behavior as **2D compatibility (EFB access)**,
default on.

Evidence:

- `work/evidence/08-legal-screen.png` (legal notice, SpongeBob reading)
- `work/evidence/09-title-screen.png` ("PRESS START" title, 59.95 fps)
- `work/evidence/10-gameplay-efb.png` (3D gameplay)
## Validation performed

| Test | Result |
|---|---|
| ISO import into clean app folder | PASS, DOL hash identical |
| RVZ import into clean app folder | PASS, DOL hash identical |
| Existing folder picker / `default-game.txt` | Pending GUI automation; path code exercised via `--game` |
| Launcher Play path (`--play`) | PASS, runner started with game title and FPS |
| Wrong disc ID | Rejected: expected disc ID GSQE78 |
| Missing game folder | Rejected: game root is not a readable directory |
| Invalid `msaa` value | Rejected: msaa must be 1, 2, 4 or 8 |
| Legal screen | PASS with the shipped EFB setting | 
| Title screen | PASS at 59.9 fps (release build, `SpongeBobRecomp.exe --play`) |
| Gameplay, living room | PASS, 59.3-60.5 fps, speed 1.00 |
| Unlocked speed | PASS, title at 86.1 fps / 1.42x |
| VSync on | PASS, locked at 59.95 |
| 16:9 widescreen | PASS, wider 3D view, HUD correct |
| 4:3 standard | PASS (same as auto for this title) |
| 4K internal resolution | PASS, 3840x2949 frame, textures crisper |
| MSAA 4x + AF 16x | PASS, `GFX.ini` shows `MSAA=4`, `MaxAnisotropy=4` |
| MSAA 8x + SSAA | PASS visually; GPU-bound at 1080p (0.61x) |
| Release folder, RVZ import | PASS, identical DOL, 338 files / 601,702,268 bytes |
| Release folder, ISO import | PASS, identical DOL |
| Release folder `--play` | PASS, legal screen, then title at 59.9 fps |
| `--set` invalid value | Rejected, file left unchanged |
| `--set` valid values | Persisted, applied to `GFX.ini` |

## Remaining work

- Level transitions and a full story playthrough are not scripted yet; the
  hub room, title, legal screens, menus, movement, camera, save states and the
  memory-card path are tested.
- Netplay was not exercised in this build.