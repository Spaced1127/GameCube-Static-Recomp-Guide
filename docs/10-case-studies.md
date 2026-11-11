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
   current image before every present. v0.1.5 adds the final shutdown guards:
   the presenter skips its frame-pacing sleep while the core is stopping, and
   an 8-second watchdog covers any remaining Vulkan/shader wait. See
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
- v0.1.4 fixed the fullscreen ALT+F4 crash with the delayed/external
  fullscreen model and swap-chain validation. v0.1.5 completes the fix with
  the presenter sleep guard and watchdog:
  `SpongeBobRecomp-v0.1.5-Windows-x64.zip`, 28,798,822 bytes, SHA-256
  `635D14337B3676388470CA3016DEF7C03EC561027D8716454FDC98EFD4F3A973`.

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

- `game.kind: "iso_or_folder"`; `check.ids` = `["GBQE78"]`, `check.file` =
  `"sys/main.dol"`; Redump dumps.
- `rpbb_launch.exe` handles prepare/start, including `--install` and
  `--window-mode`.

### What later builds added

- **Affinity is a real win.** On a Ryzen 7 7800X3D (8 cores / 16 threads), the
  main thread and the DSP LLE thread shared SMT siblings. Pinning the process
  to `0xFF` (physical cores 0-7) moved title/loading from **47.7 to 58.5 FPS**;
  main-thread load fell from 95.3% to 84.7%. The launcher sets
  `ProcessorAffinity = 0xFF` and `PriorityClass = High`.
- **PGO had been running on the default loop budget.** Generated C defaults to
  `DOLRECOMP_C_LOOP_CYCLE_BUDGET 256` / `DOLRECOMP_C_MAX_CALL_DEPTH 24`; the
  shipping modules must pass `4096` / `128` explicitly. Check
  `module-pgo/CMakeCache.txt` rather than trusting the build script.
- **The training run can "fail" and still produce a profile.** The PGO run
  exited `0xC000001D` when the window was closed, so the tool refused to merge,
  but `GBQE78-148804.profraw` (12 MB, 1,197 functions, 704,004 blocks) was
  valid. `llvm-profdata merge` by hand worked; the profile-use module reached
  **44.8 FPS vs 35.7** on the title screen before the Clang flags were applied.
- **Rumble was causing a gameplay stutter.** Controller writes from the CPU
  thread stalled a frame during landings and collisions. v0.1.2 moves rumble to
  a dedicated thread, averages the game's rapid pulse train into a steady
  value, and cuts the timeout from 10 s to 3.33 s.
- **Custom DSP microcode, not stock AX.** `DSPLLE: iram_crc 4e8a8b21` then
  `Copy new UCode ...` is the evidence that HLE will only produce zeros. LLE
  plus `dsp_rom.bin`/`dsp_coef.bin` is required, and the last "silence" was a
  muted `moderngekko-run` in the Windows per-app mixer.
- **Saves are a folder card.** `%LOCALAPPDATA%\RocketPowerRecomp\GC\USA\Card A`
  takes `.gci` files; Dolphin card images (`.raw`, `.mcd`) are not read
  directly.

### Lessons

- The same runtime already supports both cores; selecting JIT is a config/arg
  decision, not a separate engine.
- A JIT playable release plus a static artifact is a valid, honest packaging
  strategy.
- `iso_or_folder` + `check.ids` + `check.file` is a good GameCube manifest when
  both ISO and extracted folders are supported.
- Keep the manifest and launch helper in sync; the env must be set before the
  runtime selects its CPU core.
- Before blaming codegen, check the host: affinity, priority, shader cache
  directory and a warm pipeline cache are worth more than another PGO pass.

## Aggressive Inline (GILE51)

Repository: <https://github.com/Spaced1127/Aggressive-Inline-Static-Recomp>

### Identity

```text
Disc ID:      GILE51
Region:       USA / NTSC-U
Redump size:  1459978240
Redump CRC32: 5D9F46F1
DOL SHA-256:  f3d92f4312dafa5baa79355a03989873e100b97ae85b97280bc808edb084c27a
Entry point:  0x80005308
BSS:          0x801817E0 + 0x52A00
```

Engine: Z-Axis / Acclaim (`Z-Axis Gaming Environment`). CRI h4m movies,
`.zsd` audio banks, `.zal/.zit/.geo/.ins/.txr/.map/.zif/.zsc` assets.

### Build and runtime

- DolRecomp C backend: 340,568 instructions, **0 unknown**, 84 chunks,
  100 SMC candidate ranges (mostly cache management and SDK relocation writes).
- Clang `-O3` + `x86-64-v3` + ThinLTO: 36.9 MB module vs 93.1 MB for MSVC
  `/O2`; 59.9 FPS at 3x native (1920x1344), `speed~0.999`.
- DSP LLE + Cubeb audio; save states; DualSense profile; ISO/RVZ import with
  `GILE51` and DOL hash checks.

### What went wrong and how it was fixed

1. **Settings were saved but did nothing.** `aspect=wide` and
   `widescreen_hack=true` were in `config.ini`, yet the game stayed 4:3. The
   shipped runner was a stale `moderngekko-run.exe` built before the runtime
   had aspect support: it did not contain the strings `widescreen_hack` or
   `aspect=%d` and never printed `[video]`. Fix: rebuild the runner from the
   current runtime sources, pass `--core static` explicitly, and keep the new
   generic runner. Proving it: `[video] ... aspect=1 widescreen=1` plus a frame
   dump at 1844x1416 (4:3) vs 2459x1416 (16:9 Hor+).
2. **The shader cache directory did not exist.** Dolphin creates
   `Cache\Shaders` with a single-level `File::CreateDir`, which fails when
   `Cache` is absent (`CreateDir: failed on .../Cache/Shaders/`). Every launch
   rebuilt pipelines and first use appeared as CPU frame-time spikes. The
   launcher now creates the directory; after that the runtime writes
   `Vulkan-Pipeline-*.cache`, `Vulkan-uber-vs/ps-*.cache`,
   `Vulkan-specialized-*-<ID>-*.cache` and `Vulkan-gs-*.cache`.
3. **One captured window showed 1.5 s CPU stalls.** GPU busy was 2-3 ms while
   the frame took 1539.7 ms and 550.9 ms; the GPU was idle, so it was CPU-side.
   A later warm-cache run did not reproduce it in the observed window and the
   game log had no `Loading scene data` line, so it was **not** attributed.
   That honesty matters: a stall with no log line and no reproduction is an
   open question, not a fix.
4. **A host function was missing.** The zgui overlay logged
   `Host function not Found` for `inlineOverlayGetNumContinues`. It is a UI
   path, separate from the frame-time work, and belongs on the host-function
   inventory (implement or stub it deliberately, do not let it spam).
5. **"Silent audio" was a mute.** The DSP was fine; `gile.exe` was muted in the
   Windows per-app volume mixer. The earlier DSP dumps were recorded while
   muted and were not evidence of a DSP bug.

### Lessons

- A stale runner reproduces as "the setting is ignored". Check the binary's
  strings and the `[video]` line before debugging the parser.
- The launcher owns more filesystem state than it looks: shader cache, user
  dir, controller profile, `Sys/GC` DSP ROMs. Create them; do not rely on the
  runtime to create nested directories.
- A 60 FPS title with 1.5 s stalls is a CPU-side asset/shader burst until
  proven otherwise. Capture with the pipeline cache warm before optimizing
  codegen.
- CPU affinity (physical cores only) is a one-line change that can be worth
  ~20%; it also removes DSP-thread contention that looks like a codegen
  problem.

## WWE WrestleMania X8 (GW3E78)

### Identity

```text
Disc ID:      GW3E78
Region:       USA / NTSC-U
Disc size:    1459978240
DOL SHA-256:  91af3136f2a48c18a6b96a5726d1f171c9e714bb8d4d504f835070fc230a303e
Entry point:  0x800051FC
BSS:          0x80206B60 + 0x99F90
FST:          5,773 entries, 5,266 files extracted
```

Engine: Yukes `adm` (`menu/`, `bg/`, `model/`, `motion/`, `sound/`,
`adm/sheet/<brand>/`). Module: 415,760 instructions, 0 unknown, 102 chunks,
103 SMC ranges.

### Results

| Module | FPS in-match | Speed |
|---|---:|---:|
| MSVC `/O2` | 40.7 | 0.674 |
| Clang `-O3` | **59.94** | **1.0017** |

Menus hold 59.94; in-match holds it with pad input being injected. Boot to the
system-data prompt is ~45 s wall time; that is data loading, not emulation
speed.

### What the automation protocol had to do

- Automation was the **only** reliable input path. Synthetic
  `keybd_event`/`SendKeys` did not reach the game even with a keyboard
  `GCPadNew.ini`.
- The **first pad command after `--load-state` is swallowed**. Send it again.
- Short A taps (3 frames, repeated every 3 s) advanced menu -> character select
  -> arena -> match. Long holds were ignored on the arena screen.
- Never send the all-buttons combo: it includes B and backs out into the
  attract demo.
- Screenshots come from the guest framebuffer, so they work while the window is
  behind another application.

A save-state ladder made every later run cheap:

```text
menu.sav -> mainmenu.sav -> charsel.sav -> matchup.sav -> match.sav
```

### Controller finding

In WMX8 the D-pad is **taunt**, and the menus read only the main stick. D-pad
Down leaves the highlight on EXHIBITION. The fix is a launcher-side remap that
folds the D-pad into the main stick and gates taunts behind L1
(`-StockDpad` restores the shipped layout). Do not assume a GameCube game's
D-pad is movement; test it on a menu before shipping a profile.

### Lessons

- The automation protocol is a first-class test tool, not a fallback. It gives
  deterministic input, framebuffer screenshots and state capture.
- Build the state ladder early; it turns "navigate the menus again" into one
  command.
- Verify input on the game's own menus. A mapping that works in a match can be
  wrong in a menu.
- 410 FST entries with Japanese developer-leftover names are absent from disk;
  the game runs without them. Missing files are not automatically a bug.
- Audio was initialized but never auditioned; say that in the state file rather
  than claiming it works.

## WWE WrestleMania XIX (GW9E78)

### Identity

```text
Disc ID:      GW9E78
Region:       USA / NTSC-U
Disc size:    1459978240, CRC-32 635116c6
DOL SHA-256:  627b899760d0b820c049ad29f96a613da1c43d35dd4a1456e581cc620bae9fb7
DOL size:     3,422,144
Entry point:  0x80003154
BSS:          0x8033F800 + 0x5E2A0
FST:          5,015 entries
```

Generated C: 177 chunks, 103 SMC candidates. The DOL ships **retail debug
strings**, so named subsystems are available without a symbol map
(`Begin Initialize Game...`, `DVDCheckDisk = %d`, `CRender)init RenderMode.`,
`error : Already moved to ARAM.`, `NOW LOADING`, ...). Use them as grep targets
before disassembling.

### The bug worth remembering: non-ASCII paths abort the process

`ModernGekko/src/runtime/game.cpp`, `HashDirectorySha256`:

- the comparator called `std::filesystem::relative(...).generic_string()`;
  `generic_string()` converts a wide path to the ANSI codepage and **throws**
  when a name cannot be represented;
- the manifest loop had the same `path.generic_string()` problem;
- the exception escaped `InspectGame`, `std::terminate` called `abort()`, and
  the process died with `0xC0000409` (`STATUS_STACK_BUFFER_OVERRUN`, i.e.
  `__fastfail`). `moderngekko-port inspect` crashed on this disc, and the
  runner would have crashed on load.

WrestleMania XIX ships two developer-leftover PSDs with Shift-JIS names, and
WMX8 has 410 Japanese-named FST entries. Fix: sort with `lexically_relative()`
(pure lexical, no encoding conversion) and build the manifest name with
`generic_u8string()`. Byte-identical for ASCII trees, so asset hashes do not
change. Verification: `inspect` passed with the two PSDs quarantined and failed
after restoring them; after the patch it passes on the full 4,222-file tree.

### Toolchain and runtime notes

- **MSVC for the runtime, Clang for the generated module.** A GNU-style Clang
  build of the vendored Dolphin tree fails in `Externals/libusb`
  (`redefinition of 'timespec'` against the Windows 10 SDK UCRT). Clang is
  still the right compiler for the game C.
- **Runner version drift is real.** This ModernGekko has no `--core jit|static`
  flag; core selection is `--module`, `STATICRECOMP_MODULE` or
  `build/modules/<ID>/active-module.txt`. Write the guide's commands against
  the runtime you actually have, and record the difference.
- **A wrong device string fails silently.** The format is
  `Source/Id/Name` (`SDL/0/DualSense Wireless Controller`,
  `DInput/0/Keyboard Mouse`). A bad string still loads (`loaded=1`) and binds
  nothing; there is no error. Prove the pad path end to end instead: bind
  `Buttons/A = \`Battery\`` and confirm the guest reports `buttons=0x0100`.
- **No `GCPadNew.ini` means no input at all.** The frontend has no in-game
  input menu, so the title screen is as far as it gets.
- **Read `fps` after warm-up.** During boot/loading, instantaneous `fps` reads
  2-3 while assets stream; `vps` and `speed` stay near 1.0 and then it settles
  at 59.94.
- **ARAM is used for audio.** If the runtime's `AR` transfers are incomplete,
  the mixer stalls rather than erroring.
- The first run creates `work/user/GC/USA/Card A/78-GW9E-...wmx9_sys.gci`;
  the match flow loads System Data before it will start.

### Lessons

- `0xC0000409` during inspect or boot can be a `std::filesystem` encoding
  throw, not a stack overflow. Look for non-ASCII names in the extracted tree.
- Retail debug strings are free documentation. Grep them before disassembly.
- A controller profile that "loads" is not a controller that works. Verify at
  the guest pad register.
- Toolchain split (MSVC runtime, Clang module) is a choice to write down, not
  an accident.

## Asset and secondary-target work

The Rocket Power decomp project added two things this guide now covers
separately: the retail archive/asset formats
([12-asset-formats.md](12-asset-formats.md)) and the non-Windows paths
([13-other-targets.md](13-other-targets.md)). The lesson from both: a portable
reader/decoder with a host harness produces evidence you can trust, and a
"Dolphin on a handheld" result is an emulator port, not a static recomp.
