# 05 - Performance

## Method first

Use one deterministic save state, one config and one command line. Record:

- `status.txt`: `fps`, `vps`, `speed`, `frame_count`, `present_count`, `title`
- log tail: `[video]`, `[audio]`, `[staticrecomp]` shutdown stats
- exact settings, core (static/JIT), build hash, external load

A 20-30 second run is enough for a steady scene. For a full check, sample at
15/30/45/60 s. Do not compare runs while a build, PGO merge, local LLM or
other GPU workload is running.

## The first split: CPU or GPU?

Run the same state twice:

| Run | Settings |
|---|---|
| Low | 1x internal resolution, no MSAA/SSAA, AF 0, vsync off |
| High | the shipped settings, vsync off |

- Low is much faster -> **GPU-bound**. Lower MSAA/SSAA/resolution or raise the
  GPU budget.
- Low barely moves -> **CPU-bound**. GPU settings cannot fix it.

SpongeBob Bikini Bottom outside the house:

```text
1080p MSAA 8x: 42.1 fps / 0.704x
1x no AA:      42.8 fps / 0.714x   <- CPU-bound
```

The same state through Dolphin's JIT core:

```text
1080p MSAA 8x, JIT: 59.94 fps / 1.000x
```

That is the evidence that a static/JIT decision is warranted.

## Fix the host before the build

Two host problems look exactly like codegen problems. Check them before a
benchmark, and always note them in the result:

| Check | Failure looks like | Fix |
|---|---|---|
| `<user-dir>\Cache\Shaders` exists | first-use CPU spikes, pipeline rebuild every launch, 1-3 ms GPU with 100 ms+ frames | launcher creates the directory; compare a cold vs warm run |
| CPU affinity pinned to physical cores | 85-95% main-thread load, DSP thread at ~15% on an SMT sibling, 10-20% "missing" | `0xFF` on a 16-thread CPU, `High` priority |

Measured on a Ryzen 7 7800X3D (8 cores / 16 threads), same scene and module:

| Affinity | FPS | Main thread | DSP LLE |
|---|---:|---:|---:|
| all logical cores | 47.7 | 95.3% | 17.5% |
| physical cores 0-7 (`0xFF`) | **58.5** | 84.7% | 15.6% |

This is not a substitute for codegen work, but it is a one-line change and it
changes the baseline you are about to optimize.

## Frame-time capture

`status.txt` gives averages; a 1.5 s stall hides inside a 59.8 average. Capture
per-frame times when the symptom is "it hitches" rather than "it is slow".

PresentMon 2.5.1 was used with `--process_name <exe>`, `--output_file <csv>`
and `--no_console_stats`. Two traps:

- `--timed` and `--stop_existing_session` can hang and leave a stale ETW
  session. Start PresentMon detached with a unique `--session_name`, then start
  the game, then stop the process and terminate the session by name.
- Stop the capture before closing the game, or the last frames can be the
  teardown.

Read p50/p95/p99 and the count above 33/50/100 ms, not only the average:

```text
smooth window: 530 frames, 8.84 s -> 59.84 FPS
  p50 16.69 ms   p95 17.30 ms   p99 18.06 ms
  3 frames > 20 ms, 1 frame > 33 ms, GPU busy 2-3 ms

stall window: 229 frames, 8.89 s -> 25.71 FPS
  37 frames > 50 ms, 31 > 100 ms
  worst 1539.7 ms, 550.9 ms, then a ~3.5 s burst of 100-133 ms frames
  CPU busy tracks frame time; GPU 2.1 ms
```

When GPU busy is 2-3 ms and CPU busy matches the frame, it is a **CPU-side
stall**. Before calling it a codegen problem:

1. Is the pipeline cache warm (`Cache\Shaders` exists)?
2. Does the log have a load line at that time (`Loading scene data`)?
3. Did the window include a pause, menu, minimize or alt-tab?
4. Does it reproduce from a save state with no other app running?

If the answer is "no log line, no reproduction", record it as an open question.
The Aggressive Inline project captured exactly this window and did not attribute
it; that is the right outcome, not a guessed fix.

## Measured progression (SpongeBob living room)

From the performance notes, same state, Vulkan, EFB considerations as noted:

| Configuration | fps | speed |
|---|---:|---:|
| MSVC `/O2` C module (no EFB) | 27.8 | 0.469 |
| Clang `-O3` C module (no EFB) | 46.8 | 0.762 |
| + cache-op codegen fix | 49.9 | 0.826 |
| + `-march=native` | 52.6 | 0.881 |
| + loop 2048 / call 128 | 56.0 | 0.948 |
| PGO (2048/128) | ~57 | ~0.95 |
| PGO + loop 4096 | ~57-59 | ~0.94-0.97 |
| PGO 4096 with EFB on (older build) | 54.3 | 0.902 |
| JIT reference with EFB on | 60.7 | 1.000 |

Final shipped static build (before the JIT default):

| Run | Result |
|---|---:|
| Living room, 30 s | 59.28 fps / 0.999x |
| Living room, 60 s | 58.5 -> 59.5 -> 59.6 -> 60.5 fps |
| Title screen | 59.9 fps |
| Title, unlocked (historical) | 86.1 fps / 1.424x |
| 1080p, MSAA 8x + SSAA (GPU-bound) | 53.4 fps / 0.608 |

The GameCube VI is 59.94 Hz, so `speed=1.0` is full speed.

## Cross-chunk direct calls (intro-movie fix)

| Scenario | Before | After |
|---|---:|---:|
| Intro/logo movie | 0.41x (~10 fps) | **1.00x (60 VI fps)** |
| Movie audio | distorted / DMA underrun | continuous 48 kHz, no dropouts |
| Living room, 30 s | 54.6 fps / 0.917 | **59.7 fps / 0.995** |
| Release `--play` title | 59.9 fps | 59.9 fps |

The movie still presents at its native ~24 fps while the VI runs at 60 Hz;
that is the content's frame rate, not a slowdown.

## Idle-loop skip (static core)

The frame limiter at `0x800F5F90` was the hottest block in the PGO profile
(~8.18 billion iterations). It is a two-instruction wait loop. The runtime can
call `CoreTiming::Idle()` there via:

```ini
[Core]
StaticRecompIdlePC = 0x800F5F90
```

in `Sys/GameSettings/<ID>.ini`.

Living room, Vulkan, no VSync, unlocked only for measurement:

| Configuration | Before | After |
|---|---:|---:|
| 1080p, MSAA 8x + SSAA | 61.9 fps / 1.038x | **67.7 fps / 1.119x** |
| 1440p, MSAA 8x + SSAA | - | **64.7 fps / 1.070x** |
| 1x, no MSAA/SSAA | 61.0 fps / 1.024x | **72.3 fps / 1.207x** |

The idle skip is not a universal fix. It helps when the game is actually
spinning on a VI/audio/OS event. In the outdoor scene it barely helps because
the cost is real game code, not the limiter.

## JIT vs static: the important decision

SpongeBob Bikini Bottom outside the house, 1080p/8x, same save state:

| Core | fps | speed |
|---|---:|---:|
| Static module | 42.1 | 0.704x |
| JIT | 59.94 | 1.000x |

Rocket Power: Beach Bandits made the same call: its README says the playable
release runs the JIT core at 60 FPS, while the static C module (545,088
instructions) is the 40-45 FPS artifact.

Rule of thumb:

- Static within ~5% of target -> optimize static.
- Static 10-20% short -> codegen/PGO/runtime work may close it.
- Static 40% short and JIT holds target -> ship JIT default, static optional.
  Do not burn days micro-optimizing a structural gap.

## Profiling

### PGO counts

```powershell
llvm-profdata show --topn=60 --counts merged.profdata
```

Look for:

- generated chunk loops (`...;loop_XXXXXXXX`)
- game functions (`func_XXXXXXXX`)
- runtime helpers: `ppc_cache_control`, `ni_mul`, `ni_madd_msub`,
  `fp_write_single`, `ppc_fmuls`, `ppc_fma`, `ppc_fadds`, `ppc_host_call`,
  `chassis_dispatch`, `ppc_mftb`, `ppc_psq_load_inline`

Counts are not time, but they identify candidates. A helper called 50-200
million times is worth inspecting even if each call is short.

### Dispatch samples

Run with:

```powershell
$env:STATICRECOMP_DISPATCH_SAMPLES="1"
runner ... --automation-dir <auto>
# after 20-30 s
"command=stop" | Set-Content <auto>\commands\stop.txt
```

The shutdown prints:

```text
[staticrecomp] dispatch-site pc=8011ef4c samples=620
[staticrecomp] dispatch-site pc=80287df8 samples=565
...
```

Map a PC with `tools/dol_disasm.py` and the generated chunk file. The idle loop
showed only 78 samples in the outdoor scene, so it was not the outdoor
bottleneck.

### Host time

If available, use a sampling profiler (Windows Performance Recorder/WPA or
PerfView) to separate module time from Vulkan/Dolphin threads. Kernel CPU
sampling may require elevation. Without it, use the CPU/GPU split, dispatch
samples and PGO counts.

### External load

Check GPU engine counters and running processes. A local `llama-server`,
browser or compositor using 80%+ GPU compute can make a maxed MSAA/SSAA
profile dip even when the port is fine. Reproduce with it closed before
blaming the port.

## Optimization catalog

### Toolchain

- Clang `-O3`, ThinLTO, `x86-64-v3`, `-mtune=generic`.
- `-march=native` for a separate machine-specific module.
- PGO from representative gameplay.
- Loop budget 4096, max call depth 128.

### Emitter/runtime

- Cache-op inline emission; no fallback/return per `dcbf`/`dcbst`/`dcbi`/`icbi`.
- Cross-chunk direct calls + chunk table init.
- Idle-loop skip for known wait loops.
- Fast path for host calls when no mods are loaded (avoid map lookups).
- Inline/streamline `ppc_mftb`, `ppc_cache_control`, FP helpers where safe.
- Consider lazy FPRF/FPSCR updates only with careful semantic tests.
- Avoid unnecessary `ctx->pc` materialization; keep it before calls, faults,
  exceptions and dispatcher boundaries.

### Runtime/graphics

- EFB access on for 2D screens; keep the fast copy path.
- Vulkan vs OpenGL; Vulkan is usually faster.
- Resolution/MSAA/SSAA/AF affect GPU only.
- VSync off for headroom measurement; on for shipping.
- Frame cap at 1.0.

### Host

- Pin the process to physical cores (`0xFF` on 16 threads) and set `High`
  priority; do not pin to a single core.
- Create `<user-dir>\Cache\Shaders` and warm the pipeline cache before a
  benchmark.
- Move controller rumble writes to their own thread and coalesce the pulse
  train.
- Close background GPU/CPU load (browser, capture card, local LLM, build) and
  note it in the result.
- Run the same scene at 3x native to prove the CPU holds 59.94 when the GPU has
  headroom (Aggressive Inline: 59.84 average at 1920x1344, GPU 2-3 ms).

### What not to do

- Do not enable fast-math to gain a few percent.
- Do not remove SMC/exception checks for speed.
- Do not lower resolution to fix a CPU bottleneck.
- Do not compare runs with a local LLM or build running.
- Do not assume 59.9 is a dip; it is 59.94 Hz.

## Performance acceptance

- [ ] Same state before/after.
- [ ] Low/high GPU split documented.
- [ ] JIT reference recorded.
- [ ] `speed` ~1.0 and `fps` ~59.9 steady.
- [ ] No new fallback/SMC/exception regressions.
- [ ] External GPU load noted.
- [ ] If JIT default, static remains selectable and documented.
