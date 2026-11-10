# 09 - Troubleshooting

## Build

| Symptom | Cause | Fix |
|---|---|---|
| `fatal: bad revision '^master'` during ScmRevGen | no git history in the vendored Dolphin tree | harmless if the build continues; the version string may be blank |
| `rc.exe` `file not found` with a path split by a newline | `\r` from a native path in the generated `.rc` | use forward slashes in the RC icon path |
| CMake does not compile `.rc` | RC language not available | use the MSVC/Windows SDK toolchain; `CMAKE_RC_COMPILER` should point at `rc.exe` |
| module link fails with LTO/PDB issues | mixed toolchains or stale build dir | keep Clang/lld-link for the module; do not clean unless necessary |
| generated C is huge/slow | MSVC or no PGO | use Clang `-O3`, ThinLTO, PGO, loop budget 4096 |

## Boot

| Symptom | Cause | Fix |
|---|---|---|
| `no native module was supplied; use allow_interpreter explicitly` | JIT core selected without permission | set `allow_interpreter` for `--core jit`, or pass `--allow-interpreter` |
| `module loaded` absent | module not found | pass `--module` or place `g<ID>_recomp.dll` next to the exe / user modules |
| `unsupported disc ID` | wrong region/revision | use the exact supported Redump dump |
| `unsupported main DOL` | bad rip/patched DOL | verify SHA-256; use the retail DOL |
| black legal/title/menu | EFB access off | `efb_access=true` |
| no controller | no GCPadNew.ini | auto-detect first SDL gamepad; generate the profile |
| audio crackle/dropouts | DSP/HLE or CPU underrun | use correct DSP LLE/HLE, Cubeb, check CPU load; test `--audio Null` |

## Window / shutdown

| Symptom | Cause | Fix |
|---|---|---|
| `0xC0000005` at `VKGfx::BindBackbuffer` when closing fullscreen; write to `[rcx+0x40]` with `rcx=0` | swap-chain recreation cleared the images but `IsCurrentImageValid()` still returned true; current texture null | check index/texture/framebuffer; invalidate on destroy; guard null `VkSwapchainKHR`; apply fullscreen after video init |
| Fullscreen ALT+F4 hangs, or needs two presses | runtime fullscreen teardown and power-button path; CPU thread in `Presenter::Present` while the swap chain is being cleared | delay/external fullscreen; no `ToggleFullscreen()` in the destructor; 3 s shutdown grace |
| Hidden `#32770` "Warning: Failed to re-configure swap chain images" | `PanicAlertFmt` in `SwapChain::ResizeSwapChain`/`RecreateSwapChain` | log and return `false`; caller skips the frame; no modal panic during resize/close |
| F11 leaves fullscreen at the wrong size; close restores the wrong rect | fullscreen applied before the windowed rect/style was captured | capture the windowed style/rect before entering; set both the platform and `m_window_fullscreen` flags |
| Exclusive fullscreen leaves the desktop mode changed after a crash | display mode restored in the renderer destructor after the process died | restore from the launcher/helper after the process exits; use borderless by default |
| WndProc touches config while the window is destroyed | focus/size messages after `Core::Shutdown` destroyed the Config layers | return early when the platform pointer is gone; guard handlers with `IsRunning()` |

## Performance

| Symptom | Cause | Fix |
|---|---|---|
| 40-45 fps in one area, low settings does not help | static module CPU-bound | use JIT default or optimize codegen; do not lower GPU settings |
| high settings slower, low settings much faster | GPU-bound | lower MSAA/SSAA/resolution; check GPU driver/external load |
| 59.9 fps shown | 59.94 Hz VI | full speed; not a dip |
| dips only when another app runs | external GPU/CPU load | close/pause LLM/browser/build; retest |
| title 0.0 for several seconds | shader/JIT warm-up | wait for shader compile; benchmark steady state |
| unlocked option absent | intentional | speed is clamped to 1.0; target 60 |

## Logs

| Line | Meaning |
|---|---|
| `[staticrecomp] module loaded ... entry=...` | module accepted |
| `SMC: chunk ... accepted data-only write` | expected SMC write |
| `SMC: chunk ... hash mismatch; interpreter until next invalidation` | code changed; runtime falls back |
| `fallback=0` | no interpreter fallback in steady state |
| `smc_failed=0` | no failed SMC chunks |
| `native_exc=...` | module exceptions; compare relative counts |
| `hook_fb=...` | EFB/framebuffer hooks; runaway counts need diagnosis |
| `[video] backend=...` | settings actually applied |
| `[audio] mute=...` | audio settings applied |

## RecompLauncher

| Symptom | Cause | Fix |
|---|---|---|
| "That Copy Didn't Work" | compressed RVZ picked with `kind: iso` | convert to ISO |
| no ISO found automatically | no GameCube `check` exists | player picks the file; label must say ISO/region |
| setup fails | extractor non-zero, bad disc/DOL, path | run `--extract` manually, read the exit code/progress |
| verified badge missing | size/CRC mismatch | use a clean Redump dump |
| settings don't apply | wrong config path/section | inspect the file after changing; check `[video]` log |
| release not updating | 6-hour cache or same tag | Check Now; bump version for real updates |
| manifest ignored | not at top of zip or invalid JSON | put it next to the exe; validate schema |
| game data in zip | packaging bug | scan and refuse; never ship `Game/`, ISO/RVZ/DOL |

## Icons

| Symptom | Cause | Fix |
|---|---|---|
| exe has default icon | no RC resource or wrong target | add `.rc` to both targets; rebuild |
| icon path not found | path with `\r`/spaces | forward slashes, quote the path |
| icon looks blank at 16px | source too detailed | simplify/crop; include 16/24/32 sizes |
| taskbar icon differs | window class icon | set the window icon explicitly if needed |

## Debug order

1. Confirm the command line and config.
2. Read the first error/line in the log, not the last symptom.
3. Reproduce from a save state.
4. Compare static vs JIT, low vs high, vsync on/off.
5. Change one variable; record the result.
6. After three similar failures, stop and change approach.
