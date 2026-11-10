# 04 - Runtime, launcher and CPU core

## Runner

The runner is the game process. Typical invocation:

```powershell
SpongeBobRecompRunner.exe `
  --game "D:\Games\...\Game" `
  --module "D:\Games\...\gGSQE78_recomp.dll" `
  --user-dir "C:\Users\you\AppData\Local\SpongeBobRecomp" `
  --core jit `
  --graphics Vulkan --audio Cubeb
```

Useful options:

```text
--game <extracted-root>
--module <path>
--core jit|static
--user-dir <path>
--load-state <file>
--graphics Vulkan|OpenGL
--audio Cubeb|Null
--fullscreen / --windowed (template-dependent)
--automation-dir <dir>
--allow-interpreter
--headless
```

`default-game.txt` can hold a path relative to the executable (portable mode)
or user directory. The launcher writes it after import.

## CPU core selection

The runtime supports two CPU cores:

| Mode | Selection | Behavior |
|---|---|---|
| Static recomp | default, or `--core static` | loads `g<ID>_recomp.dll`, runs generated game code |
| JIT | `MODERNGEKKO_STATICRECOMP=0` or `--core jit` | uses Dolphin JIT64/JITArm64; static module ignored |

Implementation points:

```cpp
// dolphin_runtime.cpp
PowerPC::CPUCore SelectCPUCore() {
  static const bool static_recomp = [] {
    const char *v = std::getenv("MODERNGEKKO_STATICRECOMP");
    return !v || !*v || *v != '0';
  }();
  return static_recomp ? PowerPC::CPUCore::StaticRecomp
                       : PowerPC::CPUCore::JIT64;
}
```

`SelectCPUCore()` uses a function-local static, so set the env **before** the
first runtime start. The runner's `--core` path does this and:

- sets `MODERNGEKKO_STATICRECOMP` to `0` or `1`
- skips static-module discovery for JIT
- sets `config.allow_interpreter = true` for JIT, otherwise boot fails with
  `initialization failed: no native module was supplied; use allow_interpreter
  explicitly`

The module is normally auto-discovered as:

```text
<exe-dir>/g<disc-id>_recomp.dll
<user-dir>/StaticRecompModules/g<disc-id>_recomp.dll
STATICRECOMP_MODULE=<path>
```

A minimal `--core` implementation:

```cpp
// parse
else if (arg == "--core") {
  const std::string selected = value("--core");
  if (selected != "jit" && selected != "static") {
    std::cerr << "--core must be jit or static\n";
    return 2;
  }
  core_mode = selected;
}

// after config load, before Runtime::Start
if (core_mode.empty()) core_mode = frontend_config.cpu_core;
#if defined(_WIN32)
_putenv_s("MODERNGEKKO_STATICRECOMP", core_mode == "static" ? "1" : "0");
#else
setenv("MODERNGEKKO_STATICRECOMP", core_mode == "static" ? "1" : "0", 1);
#endif
if (core_mode != "static") config.allow_interpreter = true;

// skip module discovery in JIT mode
if (core_mode != "jit" && module_path.empty()) { /* discover */ }
if (core_mode != "jit" && !module_path.empty()) config.module = ...;
```

## Config

The frontend config is `config.ini` under the user directory. It is flat; the
game parser ignores section headers. The launcher and runner share it.

```ini
[Video]
resolution=1920x1080
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
cpu_core=jit
```

- `resolution` is the internal EFB scale, not the window size.
- `efb_access=true` is required for the legal/title/menu screens.
- `emulation_speed` is clamped to `1.0`; do not expose 150/200/unlocked.
- `cpu_core=jit|static` is read when no `--core` is passed.
- The launcher writes `cpu_core` and `emulation_speed=1.0` on save.

The speed clamp is intentionally in the parser, so old configs cannot bypass
it:

```cpp
} else if (key == "emulation_speed") {
  char *end = nullptr;
  const float speed = std::strtof(raw_value.c_str(), &end);
  if (end != raw_value.c_str() + raw_value.size() ||
      !std::isfinite(speed) || speed < 0.0f || speed > 4.0f)
    return {.error = "emulation_speed must be between 0 and 4"};
  // 60 Hz only; 0/1.5/2.0 from old configs load at 1.0.
  config.emulation_speed = 1.0f;
}
```

Dolphin's own `Config/Dolphin.ini` and `Config/GFX.ini` may be used by some
templates for resolution/backend/audio. Keep the split documented; don't put
the same setting in two files without a precedence rule.

## Launcher

The ImGui launcher handles:

- disc import/extraction (`--extract <iso>` for RecompLauncher)
- `default-game.txt`
- retail DOL verification
- graphics/audio/controller/savestate UI
- CPU core UI on PERFORMANCE
- starting the runner with the selected args

`--play` starts the configured game immediately (useful for automation). The
launcher's child process inherits the environment; it passes `--core` explicitly
so the selected core is unambiguous.

### Extract progress

RecompLauncher's prepare step needs headless progress:

```text
progress 0.000 Opening game.iso
progress 0.050 Extracting game files
progress 0.960 Verifying extracted files
progress 1.000 Extraction complete
```

Implement it in `--extract` only; do not open a window. Exit 0 on success.
The launcher can reuse an existing `Game/` extraction ("Using existing
extraction") but should still validate it.

### Controller

- Detect the first SDL gamepad and generate `Config/GCPadNew.ini` when no
  profile exists, so a fresh RecompLauncher install is controller-ready.
- Keep `SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS` off by default; the launcher's
  overlay also uses the pad.
- Map the standard GameCube buttons and document the mapping in `PLAYERS.md`.

## Savestates

- In-game F1 writes to `<user-dir>/StateSaves/state-YYYYMMDD-HHMMSS.sav`.
- The launcher lists `StateSaves` and can pass `--load-state` on Play.
- Savestates are large (20-50 MB) and game/version-specific; never commit them.
- For deterministic benchmarks, always use the same state and note its path.

## Window and log

- The title bar shows `Game Name | 59.9 FPS` when enabled.
- `Logs/ModernGekko.log` contains `[video]`, `[audio]`, `[staticrecomp]` and
  shutdown stats.
- Fullscreen startup, borderless sizing and clean shutdown are platform work;
  test both windowed and fullscreen.

## Fullscreen and shutdown (Windows)

The fragile part is the window/swap-chain teardown, not the renderer. The
Rocket Power and SpongeBob ports converged on the same model:

1. Create the window **windowed**.
2. Let `VideoBackend::Initialize()` create the swap chain against that window.
3. After boot, apply borderless fullscreen to the same HWND: clear the
   overlapped style and `WS_EX_CLIENTEDGE`, remove the menu, and
   `SetWindowPos` to the monitor. The Rocket Power launcher does this from
   outside the runner; SpongeBob does it from the platform's first main-loop
   iteration after the video backend is ready.
4. Keep a `m_fullscreen` flag for F11/Alt+Enter and UI state, but **do not call
   `ToggleFullscreen()` in `~PlatformWin32()`**. Destroy the borderless window
   directly. A borderless fullscreen window has no display mode to restore.
5. If you support exclusive fullscreen, restore the display mode from a
   separate owner (launcher/helper) after the process exits, not from the
   renderer destructor.

Why this matters:

- Applying fullscreen before `VideoBackend::Initialize()` can create the swap
  chain against a window whose surface/mode changes during boot. The first
  `WM_SIZE`/recreate then races the first present.
- Toggling fullscreen in the destructor sends `WM_SIZE` after `Core::Shutdown`.
  The presenter can still be in its last frame, and the swap chain's images may
  already be cleared.
- A failed `RecreateSwapChain()` must not open a modal dialog. Log and skip the
  frame; never dereference the current texture unless the image is valid.

Minimum swap-chain invariants:

- `IsCurrentImageValid()` checks the image index, texture and framebuffer, not
  only the `vkAcquireNextImageKHR` result.
- `DestroySwapChainImages()` clears the validity flag and index.
- `AcquireNextImage()` returns early if the `VkSwapchainKHR` is null.
- `BindBackbuffer()` caches and checks the current texture/framebuffer before
  `OverrideImageLayout`/`TransitionToLayout`.
- Failed `ResizeSwapChain()` / `RecreateSwapChain()` / `RecreateSurface()`
  logs an error and returns `false`; the caller skips the frame.
- Give the game a short grace period for the STM power-button event, then clear
  the running flag. SpongeBob uses 3 seconds, so one ALT+F4 always exits.

Regression matrix: fullscreen close, windowed close, F11 leave/re-enter then
close, close after loading a save, and a double-close. Check WER/dumps; a
hidden `#32770` "Warning" dialog is a panic alert, not a normal close.

## Frame rate

The GameCube VI runs at **59.94 Hz**. A 59.9 title is full speed. Clamp
`emulation_speed` to 1.0 in the config loader and remove all uncap/speed-up UI.
An old config containing `0`, `1.5` or `2` should load at 1.0, not fail.

## CPU core UX

Recommended wording:

- **JIT (60 FPS, recommended)**: Dolphin's JIT core; holds 60 FPS in tested
  scenes.
- **Static recomp (faithful)**: the shipped static module; heavy scenes can
  dip below 60.

Expose the same choice in the custom launcher and in RecompLauncher. Default
to JIT when the static module is CPU-limited; keep static selectable as the
artifact.
