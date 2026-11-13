# 01 - Architecture

## The path

```text
retail disc (.iso/.rvz)
        |
        |  DiscIO / gcdisc.py / Dolphin converter
        v
  sys/main.dol + files/  (the player's extracted game)
        |
        |  DolRecomp C backend
        v
  generated/chunks/*.c  +  generated.c/h + module_tables.inc
        |
        |  Clang -O3 + ThinLTO + PGO + lld-link
        v
  g<ID>_recomp.dll  (native game code, no assets)
        |
        |  static module loaded by the runner
        v
  ModernGekko/Dolphin runtime: CPUState, memory, MMU, GX, VI, AI/DSP,
  input, audio, video backend, savestates
        |
        v
  SpongeBobRecomp.exe (launcher/settings)  ->  SpongeBobRecompRunner.exe
        |
        v
  RecompLauncher / release zip / player
```

The same runtime can also use Dolphin's **JIT** core instead of the static
module. That is a supported playable path, not a failure of the static recomp.

## Terms

- **Static recompilation**: translate the guest `main.dol` into host C at
  build time, compile it into a native DLL, and run that DLL against a
  GameCube-compatible runtime.
- **Module**: the DLL containing the generated game code and its tables. The
  runner discovers `g<disc-id>_recomp.dll` next to the executable or in
  `<user-dir>/StaticRecompModules`.
- **DOL**: the GameCube executable (`sys/main.dol`) inside the disc.
- **FST**: the disc's file system table; the extracted `files/` tree.
- **HLE/LLE**: high-level emulation of OS/DSP calls versus running the real
  firmware/DSP. Most recomps ship LLE audio and a mix of OS HLE.
- **JIT reference**: Dolphin's JIT executing the same DOL. Use it to separate
  runtime/GPU limits from static-module code quality.
- **PGO**: profile-guided optimization of the generated C.
- **EFB access**: accurate EFB reads needed by 2D legal/title/menu screens.
- **SMC**: self-modifying code; the runtime verifies code chunks and falls back
  to the interpreter when a chunk hash changes.
- **Host function**: a guest call the runtime implements natively (OS, GX, AX,
  zgui, ...). A missing one logs `Host function not Found` and returns a
  default.
- **Pipeline cache**: `<user-dir>\Cache\Shaders`; without it every launch
  recompiles shaders and the first use shows up as CPU frame-time spikes.
- **Folder memory card**: `<user-dir>\GC\<REGION>\Card A\*.gci`; not a card
  image, and `.gci` files can be copied in from Dolphin.
- **Launcher shell**: the shared launcher code behind every port. Every title
  gets the same feature set, settings layout and paths; the title supplies a
  theme, not a fork. See
  [15-launcher-parity.md](15-launcher-parity.md#the-launcher-parity-contract).
- **Theme pack**: the per-title data a launcher build consumes: product and
  executable names, icons, accent, player-facing strings and manifest labels.
  Data and art only; no game logic.
- **Idle loop**: a tight guest loop waiting for a VI/audio event; skipping it
  with `StaticRecompIdlePC` avoids millions of host iterations per frame.
- **CPU core selection**: `MODERNGEKKO_STATICRECOMP=0` selects Dolphin's JIT;
  otherwise the static module is used. `--core jit|static` is the per-launch
  equivalent.

## Project layout used by both case studies

```text
lib/ModernGekko-Template/
  lib/ModernGekko/              runtime, launcher, runner, CMake
  lib/DolRecomp/                recompiler
  lib/ModernGekko/vendor/dolphin/   Dolphin runtime + Data/Sys
  tools/                        gcdisc/rvz/DOL/disasm helpers
build/moderngekko/              CMake/Ninja build tree + executables
build/modules-call/<ID>/.../    generated C, instrumented/PGO modules
work/disc/                      disc image (never commit)
work/game/                      extracted game (never commit)
work/pgo/                       .profraw/.profdata (never commit)
work/auto*/                     automation status/screenshots/states
dist/                           release folders/zips (never commit)
docs/release/                   README.txt, recomplauncher.json
```

## Launcher/runner split

- **Launcher** (`SpongeBobRecomp.exe`): imports the disc, extracts it,
  verifies the DOL, edits `config.ini`, lists controllers/savestates, then
  starts the runner. It also owns `--extract` for RecompLauncher and the
  `PERFORMANCE` CPU-core/settings UI.
- **Runner** (`SpongeBobRecompRunner.exe`): the actual game process. It loads
  the config, selects the CPU core, boots Dolphin, runs the module/JIT,
  handles audio/video/input and writes the log.
- **RecompLauncher** starts the runner directly (not the launcher) and supplies
  `--module` / `--user-dir` and, in JIT mode, the CPU-core choice.

## Config

The frontend `config.ini` is a flat key/value file used by both the launcher
and runner. Dolphin's own `Config/Dolphin.ini` / `Config/GFX.ini` are separate
and are used by some templates/projects.

Important keys:

```ini
[Video]
resolution=1920x1080       # internal EFB scale (3x = 1080p)
backend=Vulkan
fullscreen=true
show_fps_in_title=true
msaa=8
ssaa=false
anisotropy=4
vsync=true
aspect=wide
widescreen_hack=false
efb_access=true
mute=false
volume=100
emulation_speed=1
cpu_core=jit               # jit | static

[Input]
controller1=SDL/0/DualSense Wireless Controller
```

The game's parser ignores section headers, so the keys work globally. Keep
sections for readability. The launcher's `SaveConfig` writes `cpu_core` and
`emulation_speed=1.0`.

## CPU core selection details

`SelectCPUCore()` reads `MODERNGEKKO_STATICRECOMP` once (a function-local
static), so set it **before** the first runtime start:

```text
MODERNGEKKO_STATICRECOMP=0 -> JIT64/JITArm64
anything else / unset      -> StaticRecomp
```

The runner's `--core jit` sets the env to `0`, skips static-module discovery
and sets `allow_interpreter` (required when no native module is supplied).
`--core static` sets it to `1` and loads `g<ID>_recomp.dll`.

## Runtime settings worth knowing

- `[video] backend=... scale=... msaa=... ssaa=... af=... vsync=...` is printed
  at startup; use it to prove settings reached the game.
- `EFB access` is required for legal/title/menu screens; enabling accurate
  reads with the fast copy path keeps 3D fast.
- `VSync` locks to the display; for benchmarks use `vsync=false` to measure
  headroom.
- `emulation_speed` is clamped to 1.0; the target is 59.94 VI Hz.
- `StaticRecompIdlePC` lives in `Sys/GameSettings/<ID>.ini`:

```ini
[Core]
StaticRecompIdlePC = 0x800F5F90
```

- `STATICRECOMP_DISPATCH_SAMPLES=1` prints the top guest PCs at shutdown.
- `--load-state <file>` loads a Dolphin savestate before boot.
- `--automation-dir <dir>` enables file-based control/status; see
  [06-debugging-and-testing.md](06-debugging-and-testing.md).
