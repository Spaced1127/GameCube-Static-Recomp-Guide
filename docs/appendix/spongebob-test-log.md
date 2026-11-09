# Test log — 2026-11-08

## Environment

- Windows, AMD Ryzen 7 7800X3D (8C/16T), 32 GB RAM, Radeon RX 7900 XT.
- MSVC 19.51 (Visual Studio Build Tools 18), CMake 4.5, Ninja 1.13.
- DolRecomp (ExpansionPak), ModernGekko / RecompCore vendor branch.
- Renderer: Vulkan. Audio: Null (audio not exercised).

## Build under test

- Extracted game: `work/game` (`sys/main.dol`, `files/`, `sys/boot.bin`).
- Recompiled module: `build/modules/GSQE78/<dol-sha256>-.../gGSQE78_recomp.dll`.
- Runtime: `build/moderngekko/moderngekko-run.exe`.
- Local runtime patches: `patches/dolphin-staticrecomp-data-writes.patch`,
  `patches/moderngekko-runtime-dol-data-writes.patch`.

## Tests

| # | Test | Method | Result | Evidence |
|---|---|---|---|---|
| 1 | RVZ → ISO | `tools/rvz_extract.py` | ISO `1,459,978,240` bytes; FST 425 entries / 338 files / `601,702,268` bytes | `work/disc/game.iso` |
| 2 | Retail DOL identity | `tools/verify_dol.py` | SHA-256 `dca4f72b...e009`, SHA-1 `5da8295a...6ef5`, zero byte differences in both copies | `work/evidence/dol-identity.txt` |
| 3 | Full recompile | `dolrecomp --gamecube` | 649,624 instructions; 0 unknown; 160 C chunks; 0 decode failures | `build/recomp/generated` |
| 4 | Module build | `moderngekko-port build` | Linked `gGSQE78_recomp.dll` | build log |
| 5 | Boot | `moderngekko-run --headless --automation-dir` | `booted=1`, `state=running`, `frame_count=339` after 15 s, `speed=0.998` | `work/auto/status.txt` |
| 6 | Nick Games logo | automation screenshot at 30 s | Rendered | `work/evidence/01-nick-logo.png` |
| 7 | THQ logo | screenshot at 50 s | Rendered | `work/evidence/02-thq-logo.png` |
| 8 | Big Sky logo | screenshot at 60 s | Rendered | `work/evidence/03-bigsky-logo.png` |
| 9 | Gameplay load | screenshot after Start | SpongeBob's living room, 3D models, textures, lighting, shadows, HUD icon | `work/evidence/04-gameplay-base.png` |
| 10 | Forward movement | `pad_frames main_y=1`, 90 frames | SpongeBob moved from room centre to the door; camera followed | `work/evidence/05-gameplay-forward.png` |
| 11 | Lateral movement | `pad_frames main_x=1`, 90 frames | Position/camera changed again | `work/evidence/06-gameplay-right.png` |
| 12 | A button | `pad_frames a=1`, 5 frames | Input accepted; no interaction at that distance | `work/auto9/a.png` |
| 13 | Memory-card access | Start at 100 s | Game showed “Now accessing the Memory Card in Memory Card Slot A.”; GCI folder created at `%LOCALAPPDATA%/moderngekko/GC/USA/Card A` | `work/evidence/07-memory-card-overlay.png` |
| 14 | Save state | automation `save_state` | 5.36 MB state written and later loaded successfully | `work/auto7/game.state`, `work/auto9/gameplay.state` |
| 15 | Lockstep equivalence | `STATICRECOMP_LOCKSTEP=1`, limit 30,000 | 235 checks, 234 exact, 1 divergence, 0 undercharges, 18 fallback skips | `work/evidence/lockstep.txt` |
| 16 | False-SMC fix | memory dumps of failing chunks + runtime patch | Chunks `801E72C0`, `801EF2C0`, `8028F2C0` accepted as data-only writes; `smc_failed=0` | `patches/`, stderr in `work/auto10` |
| 17 | Title / Hit Start screen | fresh boot, screenshots at 60–100 s | Screen is black at 90–100 s; pressing Start reaches gameplay | `work/auto12/t90.png` … `t100.png` |
| 18 | Pause menu | Start from gameplay state | Not confirmed; Start did not visibly open a menu in the tested scene | `work/auto11/pause_*.png` |
| 19 | Audio | — | Not tested (Null backend) | — |
| 20 | In-game save/load | — | Not tested end-to-end | — |
| 21 | Packaged ISO import | `dist\SpongeBobRecomp\SpongeBobRecomp.exe --extract work\disc\game.iso` | PASS: `Game/sys` + `Game/files` written; `main.dol` SHA-256 `dca4f72b...e009`, zero byte diff | `dist\SpongeBobRecomp\Game` |
| 22 | Packaged RVZ import | same launcher, original `.rvz` | PASS: identical extracted DOL, 1.4 GB assets | `dist\SpongeBobRecomp\Game` |
| 23 | Packaged runner from `dist` | no source-tree paths | `booted=1`, `state=running`, module loaded from app folder, `smc_failed=0` | `dist\SpongeBobRecomp\TestRun` |
| 24 | Launcher UI | software SDL renderer, screenshot | Full settings panel: backend, resolution, MSAA, SSAA, AF, VSync, aspect, widescreen, speed, 2D compatibility, folder picker | `work/evidence/11-launcher-settings.png` |
| 25 | Launcher Play path | `SpongeBobRecomp.exe --play` | Runner started from the launcher; title bar `... | 75.3 FPS` | `work/evidence/12-launcher-play.png` |
| 26 | Wrong disc ID | patched copy of ISO with `XXXXXX` serial | Rejected: expected disc ID GSQE78 | command output |
| 27 | Missing game folder | `--game` pointing at a missing path | Rejected: game root is not a readable directory | command output |
| 28 | Invalid setting | `msaa=3` | Rejected: msaa must be 1, 2, 4 or 8 | command output |
| 29 | 2D legal screen | EFB access on | PASS: legal notice renders | `work/evidence/08-legal-screen.png` |
| 30 | Title screen | EFB access on, `work/auto7/game.state` | PASS: "PRESS START" title at 59.95 fps | `work/evidence/09-title-screen.png` |
| 31 | 3D gameplay with EFB | PGO Clang module, living-room state | 54.3 fps / 0.902x | `dist\SpongeBobRecomp\EfbPlay\status.txt` |
| 32 | JIT reference with EFB | module removed from `dist` | 60.7 fps / 1.000x, proves runtime can hold 60 | `dist\SpongeBobRecomp\JitEfbPlay\status.txt` |
| 33 | Same boot, EFB off | default video | Legal/title screens black; confirms EFB is the cause | `work/auto12` |
| 34 | EFB peek-only | enable accurate EFB reads only, keep fast copy path | Legal and title screens render; identical gameplay fps to EFB off | `dist\SpongeBobRecomp\PeekTitle\title.png` |
| 35 | Shipped 2D compatibility | default config (`efb_access=true`) | Title 59.97 fps, legal 59.92 fps, gameplay 58.9-60.5 fps | `dist\SpongeBobRecomp\TitleNew`, `LegalNew` |
| 36 | Final module (x86-64-v3) | Clang -O3 PGO 4096/128, AVX2 baseline | 30 s living room: 59.28 fps / 0.999x | `tools/bench_module.ps1` |
| 37 | 60 s gameplay soak | same module, Cubeb audio | 15/30/45/60 s: 58.5 -> 59.5 -> 59.6 -> 60.5 fps; speed ~1.0; no errors | `dist\SpongeBobRecomp\Soak60` |
| 38 | Unlocked framerate | `emulation_speed=0`, title state | 86.1 fps / 1.424x | `dist\SpongeBobRecomp\UnlockedTitle` |
| 39 | VSync | `vsync=true` | 59.95 fps locked | `dist\SpongeBobRecomp\CfgVsync` |
| 40 | Aspect + widescreen hack | auto / wide / standard / hack | auto=4:3, wide=16:9, standard=4:3, hack changes 3D only | `work/evidence/13-msaa16x9.png`, `16-release-title.png` |
| 41 | 4K internal resolution | `resolution=3840x2160` | 3840x2949 frame, correct, textures crisper | `work/evidence/14-4k.png` |
| 42 | MSAA 8x + SSAA | 1080p | Renders correctly; GPU-bound (53.4 fps, vps 30.4) | `dist\SpongeBobRecomp\CfgSsaa\shot.png` |
| 43 | Save state + load | automation `save_state` / `--load-state` | 25 MB state written; loaded at 59.45 fps in the room | `dist\SpongeBobRecomp\PlayThrough\play.state` |
| 44 | Title -> gameplay | Start from fresh boot | Reaches living room, movement and A accepted | `dist\SpongeBobRecomp\PlayThrough` |
| 45 | Release folder RVZ import | clean `dist\SpongeBobRecomp-Release` | PASS, identical DOL, 338 files | `dist\SpongeBobRecomp-Release` |
| 46 | Release folder ISO import | same | PASS, identical DOL | command output |
| 47 | Release `--play` | launcher -> runner -> game | Legal screen, then title at 59.9 fps in the title bar | `work/evidence/15-release-play.png`, `16-release-title.png` |
| 48 | Release contents | asset scan | 94.5 MB, no ISO/RVZ/DOL/texture/audio data; zip 26.9 MB | `dist\SpongeBobRecomp-Release.zip` |
| 49 | 3-minute gameplay soak | 9 x 20 s movement + A, Cubeb audio | 59.93-60.82 fps, speed ~1.00 every sample, no errors, no crash | `dist\SpongeBobRecomp\Soak5m` |
| 50 | Audio output | `DumpAudio=True`, 20 s gameplay | DSP dump non-silent: 32 kHz stereo, peak 27,437/32,767, 99.9% non-zero samples | `dist\SpongeBobRecomp\UserAudio\Dump\Audio` |
| 51 | Actual game boot (test harness) | `User.tsc`: `InitGlobalAgent 23` (LVL_BBSH) | Bedroom intro with dialogue text; 59.94 fps, speed 1.000 | `work/evidence/20-bedroom-intro.png` |
| 52 | Pants pickup + level transition | walk to pants, then bedroom door | Bedroom -> living room transition; 59.98 fps, speed 1.001 | `work/evidence/21-bedroom-pants.png`, `22-living-room.png` |
| 53 | Living room gameplay | Gary, HUD, movement | HUD (doubloons/jellyfish/tiles/health), Gary NPC, 59.93 fps, speed 1.000 | `work/evidence/23-living-room-hud.png` |
| 54 | Main menu (normal flow) | Krusty Krab kitchen, flower mats | Room renders and SpongeBob moves, but no option activated with A/B/X/Y/Z/Start on a flower; under investigation | `dist\SpongeBobRecomp\MenuSave\menu.state` |
| 55 | Cross-chunk direct calls | generator fix (`emit_set_chunk_table`) | ~36,000 direct call sites; intro movie 0.41x -> 1.00x; gameplay 54.6 -> 59.7 fps | `docs\notes\07-performance.md` |
| 56 | Intro movie audio | Cubeb + DSP dump, 45 s boot | 48 kHz continuous, peak 26,868, RMS 7,924, no dropouts | `dist\SpongeBobRecomp\UserMovieAudio\Dump\Audio` |
| 57 | Pause menu | Start in living room | "GAME PAUSED", Game Totals, To Do List, Options; A selects, Y back | `dist\SpongeBobRecomp\SaveFlow\options.png` |
| 58 | Save game | Options -> Save Game -> Game 1 | Save complete; `78-GSQE-SpongeBob RFD.gci` (65,600 B) written to the card; slot shows SpongeBob's House | `dist\SpongeBobRecomp\UserSave\GC\USA\Card A` |
| 59 | Load game | Options -> Load Game -> Game 1 | Slot list shows the save; loading returns to the game | `dist\SpongeBobRecomp\LoadFlow\loadlist.png` |
| 60 | Release movie + title retest | release runner, new module, Cubeb | Movie speed 1.00 with 60 VI fps; `--play` title bar 59.9 FPS | `work/evidence/24-release-title-calls.png` |
| 61 | Redesigned launcher | graphical shell, 5 pages, custom fonts, animated underwater background | Play/Graphics/Performance/Audio/Controller pages render and navigate | `work/evidence/34-*.png` |
| 62 | Launcher audio mute | GUI checkbox -> config.ini -> runner | `mute=true`; runner logs `[audio] mute=1 volume=0`; MUTED + volume 0 applied at the backend | `dist\SpongeBobRecomp\34-audio.png` |
| 63 | Launcher volume | GUI slider | Clicking at ~60% writes `volume=50`; slider disabled while muted | command output |
| 64 | Unlock frame rate | PERFORMANCE page | Checkbox writes `emulation_speed=0` (unlocked); capped speeds 100/150/200 remain | `work/evidence/34-performance.png` |
| 65 | Release rebuild | new launcher + runner + PGO module | 100.5 MB folder, 28.4 MB zip, no game data | `dist\SpongeBobRecomp-Release.zip` |

## Lockstep divergence

One divergence:

```
entry=0x800F36D4 end=0x800F3A4C
r0:N=0x20,I=0x0 r3:N=0x0,I=0xffffffe0 r4:N=0xcc003000,I=0x80000000 ...
mmio#:N=8,I=1
```

`0x800F36D4` is in the statically linked Dolphin SDK OS area. The interpreter
side sees a different MMIO sequence, consistent with an HLE-patched SDK
function rather than a game-code recompilation error. The game blocks outside
this range matched exactly.

## Known gaps

- Level transitions and a full story playthrough are not scripted; the hub
  room, legal/title screens, movement, camera, save states and the memory-card
  path are tested.
- Pause menu not confirmed: Start advances the boot flow but did not open a
  visible pause menu in the tested living-room scene.
- Audio runs (Cubeb backend, DSP thread) but was not listened to in this
  environment.
- MSAA 8x + SSAA at 1080p is GPU-bound; the default (MSAA 1x-4x, no SSAA)
  holds 60 fps.
## Repro commands

```powershell
# Build the module
$env:Path = "C:\Users\Gamer\AppData\Local\Microsoft\WinGet\Packages\Ninja-build.Ninja_Microsoft.Winget.Source_8wekyb3d8bbwe;" + $env:Path
cmd /c '"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul && build\moderngekko\moderngekko-port.exe build work\game --backend c --toolchain msvc --output build\modules'

# Run with automation
build\moderngekko\moderngekko-run.exe --game work\game --module <dll> `
  --graphics Vulkan --audio Null --allow-interpreter --automation-dir work\auto
```

Automation commands are `key=value` files in `work/auto/commands/`; see
`tools/automation_protocol.cpp` upstream or the examples used above:

```
command=pad_frames
port=0
frames=90
main_y=1
```

```
command=screenshot
path=C:/absolute/path/shot.png
```
