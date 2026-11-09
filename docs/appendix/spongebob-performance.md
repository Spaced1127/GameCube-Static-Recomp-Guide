# Performance work and measurements

Updated: 2026-11-08

Measurements use the same living-room savestate
(`work/auto9/gameplay.state`), Vulkan, Null audio, and the automation
`status.txt` after a fixed run. Values move a few percent between runs and are
not comparable while a build or LLVM job is using the CPU.

## What was changed

1. **Clang instead of MSVC for the generated C** (`-O3`, ThinLTO).
2. **Cache-op code generation fix.** DolRecomp emitted
   `ppc_fallback_instruction(...); return;` for every `dcbst`/`dcbf`/`dcbi`/
   `icbi`, breaking the native burst (33 million fallbacks in one run). The C
   emitter now calls `ppc_cache_control` inline and continues. Fallbacks fell to
   ~18,000.
3. **`-march=native -mtune=native`** for the per-game module.
4. **Loop budget / call depth**: `DOLRECOMP_C_LOOP_CYCLE_BUDGET=2048`,
   `DOLRECOMP_C_MAX_CALL_DEPTH=128` (larger values regressed).
5. **PGO** on the generated chunks (Clang, `-fprofile-generate` → merge →
   `-fprofile-use`).
6. **EFB access** enabled for 2D compatibility (legal/title TGA screens).

## Module comparison (3D living room, EFB on)

| Configuration | fps | speed |
|---|---:|---:|
| MSVC `/O2` C module (no EFB) | 27.8 | 0.469 |
| Clang `-O3` C module (no EFB) | 46.8 | 0.762 |
| + cache-op fix | 49.9 | 0.826 |
| + `-march=native` | 52.6 | 0.881 |
| + loop 2048 / call 128 | 56.0 | 0.948 |
| PGO (2048/128) | ~57 | ~0.95 |
| PGO + loop 4096 | ~57–59 | ~0.94–0.97 |
| **PGO 4096 with EFB on** | **54.3** | **0.902** |
| JIT reference with EFB on | **60.7** | **1.000** |

The JIT reference is the runtime with the recompiled module removed; Dolphin's
JIT executes the same game code. It shows the EFB readback itself can run at
60 fps, so the remaining gap is the static module.

## EFB trade-off

The 3-4 fps cost was **not** the EFB peek itself. Forcing Dolphin's slow
EFB-copy-to-RAM path (EFBToTextureEnable=false, DeferEFBCopies=false)
is what cost the frames. Enabling only accurate EFB reads
(EFBAccessEnable=true, fast copy path kept) renders the legal and title
screens correctly and keeps the title at 59.9 fps.

- Peek-only EFB (shipped default): legal/title screens correct; 3D at the
  full no-EFB rate.
- EFB fully off: legal/title screens black.
- Full EFB completion (old test profile): correct 2D, 3-4 fps slower in 3D.

The launcher exposes the shipped behavior as **2D compatibility (EFB access)**,
default on. Two env hooks remain for diagnosis: SB_EFB_FULL=1 restores the
old completion profile, `SB_EFB_ACCESS=1` forces EFB reads on.

## Final shipped configuration

- Clang `-O3`, ThinLTO, PGO profile collected on gameplay (4096-cycle loop
  budget, 128 call depth)
- `-march=x86-64-v3 -mtune=generic` (AVX2 baseline; no AVX-512, so it runs on
  any modern x86-64 CPU, not just the build machine)
- 2D compatibility via accurate EFB reads only (fast copy path kept)

| Run | fps | speed |
|---|---:|---:|
| Living room, 30 s | 59.28 | 0.999 |
| Living room, 60 s (samples at 15/30/45/60 s) | 58.5 -> 59.5 -> 59.6 -> 60.5 | 0.97 -> 1.00 -> 1.01 -> 1.00 |
| Title screen | 59.9 | 1.000 |
| Title, unlocked speed | 86.1 | 1.424 |
| Title, VSync on | 59.95 | 0.999 |
| 1080p, MSAA 8x + SSAA (GPU-bound) | 53.4 (vps 30.4) | 0.608 |

The GameCube's VI runs at 59.94 Hz, so `speed = 1.0` is full speed. The
heaviest tested 3D scene now holds 59-60.5 fps with 2D compatibility on.

## Cross-chunk direct calls (intro-movie fix)

The C backend emitted every cross-chunk `bl` as `ctx->pc = target;
return;` even though it has a direct-call path: the generator never called
`emit_set_chunk_table`, so the chunk table was empty and the path was dead.
Every cross-chunk call therefore went back through the chassis (dispatcher,
two state syncs, downcount flush).

Initializing the global chunk table fixes that: the generated module now has
~36,000 direct call sites. The intro/logo movies were the visible symptom,
because the THP player busy-polls `AUDIO_DMA_BLOCKS_LEFT` (0xCC00503A) once
per audio block: each poll iteration was a chassis round trip.

| Scenario | Before | After |
|---|---:|---:|
| Intro/logo movie, emulation speed | 0.41x (~10 fps) | **1.00x (60 VI fps)** |
| Movie audio | distorted (DMA underruns) | continuous 48 kHz, peak 26,868, no dropouts |
| Living room, 30 s | 54.6 fps / 0.917 | **59.7 fps / 0.995** |
| Release `--play` title | 59.9 fps | 59.9 fps |

The movie still presents at its native ~24 fps (film rate) while the VI runs
at 60 Hz; that is the content's frame rate, not a slowdown. The debug profile
confirmed the movie runs at full emulated speed.
## Frame limiter idle loop (v0.1.3)

The game waits for the next VI/audio event in a tight loop at `0x800F5F90`
(`lwz r0,-17632(r13); cmplwi r0,0; beq`). It was the hottest block in the PGO
profile (~8.18 billion iterations), so the recompiled CPU spent most of its
host time spinning there. `Sys/GameSettings/GSQE78.ini` now sets
`StaticRecompIdlePC = 0x800F5F90`; when the dispatcher lands there,
`CoreTiming::Idle()` advances to the next scheduled event instead of running
the loop.

| Living room, Vulkan, no VSync | Before | After |
|---|---:|---:|
| 1080p, MSAA 8x + SSAA | 61.9 fps / 1.038x | **67.7 fps / 1.119x** |
| 1440p, MSAA 8x + SSAA | - | **64.7 fps / 1.070x** |
| 1x, no MSAA/SSAA (CPU test) | 61.0 fps / 1.024x | **72.3 fps / 1.207x** |

That matches Dolphin's JIT reference (1.208x). The shipped build caps at 60 FPS:
`frontend_config.cpp` loads every `emulation_speed` value as `1.0`, and the
custom launcher and RecompLauncher no longer expose the old 150%/200%/unlocked
options. The cap keeps 60 FPS in the living room; external GPU load can still
push a maxed-out MSAA/SSAA profile below 60.

## JIT playable path (v0.1.3)

The Bikini Bottom outdoor scene is CPU-bound in the static module. The same
newest save state gives 42.1 fps / 0.704x at 1080p MSAA 8x and 42.8 fps /
0.714x at 1x with no AA, so lowering GPU settings does not recover it.

Running that state through Dolphin's JIT core (`MODERNGEKKO_STATICRECOMP=0`)
gives **59.94 fps / 1.000x** at the same 1080p settings. The launcher and
RecompLauncher now default to JIT, with the static module selectable as the
faithful static-recompilation artifact. This is the same split used by the
Rocket Power: Beach Bandits recomp, whose playable release also runs the JIT
core while keeping its static module.

## LLVM backend (not shipped)

DolRecomp's LLVM backend was built against MSYS2 LLVM 23 after adapting the
LLVM API (`Triple`, `getOrInsertDeclaration`, `PGOOptions`, MinGW
`LLVM_DEFINITIONS`). Two module flavours were generated:

- `--runtime=moderngekko` emits an `MGNative*` module whose host ABI
  (`Core/PowerPC/Native/NativeModuleABI.h`) does not exist in this
  ModernGekko/RecompCore chassis, so it cannot be loaded here.
- The default (RecompCore) LLVM module builds and loads, but on this chassis
  it never reaches the video interface: no MMIO writes, no exception activity,
  no presented frames, and it advances only ~0.03x real time. It is not a
  drop-in replacement.

The tuned C module reaches full speed, so the released build uses it. The LLVM
path is left for a future chassis that implements the native module ABI.
