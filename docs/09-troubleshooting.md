# 09 - Troubleshooting

## Build

| Symptom | Cause | Fix |
|---|---|---|
| `fatal: bad revision '^master'` during ScmRevGen | no git history in the vendored Dolphin tree | harmless if the build continues; the version string may be blank |
| `rc.exe` `file not found` with a path split by a newline | `\r` from a native path in the generated `.rc` | use forward slashes in the RC icon path |
| CMake does not compile `.rc` | RC language not available | use the MSVC/Windows SDK toolchain; `CMAKE_RC_COMPILER` should point at `rc.exe` |
| module link fails with LTO/PDB issues | mixed toolchains or stale build dir | keep Clang/lld-link for the module; do not clean unless necessary |
| generated C is huge/slow | MSVC or no PGO | use Clang `-O3`, ThinLTO, PGO, loop budget 4096 |

## Build and extraction

| Symptom | Cause | Fix |
|---|---|---|
| module build fails deep in the object writer, error names a path near 250 characters | module cache written under a long project path with spaces | build with `--output C:\short\modules`, then copy the DLL back |
| PGO module is no faster and the profile is enormous | generated header defaults `DOLRECOMP_C_LOOP_CYCLE_BUDGET 256` / `MAX_CALL_DEPTH 24`; the `-D` overrides never reached the compiler | grep `module-pgo\CMakeCache.txt` and `build.ninja` for `DOLRECOMP_C_`; rebuild with `4096`/`128` |
| PGO helper refuses to merge after the training run | the training run exited nonzero (e.g. `0xC000001D` on window close) | the `.profraw` is usually valid: `llvm-profdata merge` manually, then check the function/block counts |
| `moderngekko-port inspect` or first boot dies with `0xC0000409` | non-ANSI (Shift-JIS) file names: `generic_string()` throws, `terminate` calls `__fastfail` | list names with the regex in [06](06-debugging-and-testing.md#non-ascii-paths); fix with `lexically_relative()` + `generic_u8string()`; do not rename retail files |
| different module hash for the same DOL | cache key includes the toolchain hash | record the `<dol-sha>-<toolchain-hash>` path in `STATE.md` |

## Boot

| Symptom | Cause | Fix |
|---|---|---|
| `no native module was supplied; use allow_interpreter explicitly` | JIT core selected without permission | set `allow_interpreter` for `--core jit`, or pass `--allow-interpreter` |
| `module loaded` absent | module not found | pass `--module` or place `g<ID>_recomp.dll` next to the exe / user modules |
| `unsupported disc ID` | wrong region/revision | use the exact supported Redump dump |
| `unsupported main DOL` | bad rip/patched DOL | verify SHA-256; use the retail DOL |
| black legal/title/menu | EFB access off | `efb_access=true` |
| no controller | no GCPadNew.ini | auto-detect first SDL gamepad; generate the profile |
| controller profile loads but nothing responds; game never leaves the title | wrong device string (`Source/Id/Name`) or a game with no in-game input menu | verify at the guest pad register; write the profile the game expects |
| audio crackle/dropouts | DSP/HLE or CPU underrun | use correct DSP LLE/HLE, Cubeb, check CPU load; test `--audio Null` |
| `Failed to initialize DSP emulation!` | `Sys/GC/dsp_rom.bin` / `dsp_coef.bin` missing next to the runner | ship both files; DSP LLE cannot start without them |
| total silence, but the game runs | wrong DSP mode, or the app is muted in the Windows volume mixer | check the per-app mixer first; then LLE/HLE; then the in-game sound menu |
| DSP HLE produces only zeros | custom/uCode not in the HLE table (`DSPLLE: iram_crc ... Copy new UCode`) | use DSP LLE; do not chase a mixer bug |
| settings saved but the game ignores them; no `[video]` log line | stale runner binary built before the option existed | rebuild the runner from the current runtime; pass `--core static` for a generic runner |
| `Host function not Found` in the log | runtime does not implement a host function the game calls (e.g. zgui `inlineOverlayGetNumContinues`) | implement or stub it once; do not let it log per frame |
| a release runs the wrong game / rejects the disc | game-specific runner enforces `MODERNGEKKO_REQUIRED_DISC_ID` / DOL hash | build a generic runner without those defines, or ship one runner per game |

## Window / shutdown

| Symptom | Cause | Fix |
|---|---|---|
| `0xC0000005` at `VKGfx::BindBackbuffer` when closing fullscreen; write to `[rcx+0x40]` with `rcx=0` | swap-chain recreation cleared the images but `IsCurrentImageValid()` still returned true; current texture null | check index/texture/framebuffer; invalidate on destroy; guard null `VkSwapchainKHR`; apply fullscreen after video init |
| Fullscreen ALT+F4 hangs, or needs two presses | runtime fullscreen teardown and power-button path; CPU thread in `Presenter::Present` while the swap chain is being cleared | delay/external fullscreen; no `ToggleFullscreen()` in the destructor; 3 s shutdown grace |
| Close still hangs after the swap-chain guards; process alive, no crash dump | CPU thread in the presenter's frame-pacing sleep while `CPUManager::Stop()` waits for `PowerDown` | skip `CoreTiming::SleepUntil()` when `Core::IsRunning()` is false; add an 8 s shutdown watchdog |
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
| 10-20% "missing" with the CPU at 95% and DSP LLE at ~15% | main thread and DSP thread share SMT siblings | pin to physical cores (`0xFF` on 16 threads) + `High` priority |
| first seconds / first use hitch, pipelines rebuilt every launch | `<user-dir>\Cache\Shaders` does not exist; Dolphin's single-level `CreateDir` failed | create the directory in the launcher; compare cold vs warm |
| frames take 100-1500 ms, GPU busy 2-3 ms | CPU-side asset/shader burst, not rendering | warm the pipeline cache, check the log for a load line, reproduce from a state before optimizing |
| stall does not reproduce and has no load/error line | capture window included a pause/menu/minimize, or a cold cache | record it as open; do not attribute a cause without a reproduction |
| handheld shows 88-95% even with a high overclock | emulation speed limit is 90%, not 100% | set speed limit to 100% before touching CPU clock override |

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
| `DSPLLE: iram_crc: ...` then `*** Copy new UCode ...` | the game uploaded custom DSP microcode; HLE will only produce zeros, use LLE |
| `Host function not Found` | a host function is missing; stub or implement it once |
| `CreateDir: failed on .../Cache/Shaders/` | nested cache path missing; create it in the launcher |

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
