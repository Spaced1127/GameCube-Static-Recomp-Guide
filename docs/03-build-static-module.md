# 03 - Build the static module

The static module is generated C compiled into `g<ID>_recomp.dll`. The gap
between a working module and a fast one is mostly toolchain and codegen, not
game-specific hand edits.

## 0. Configure the runtime

A representative configure command for the template (option names vary by
template/version; check `build/moderngekko/CMakeCache.txt` after configuring):

```powershell
cmake -S lib\ModernGekko-Template\lib\ModernGekko -B build\moderngekko -G Ninja `
  -DCMAKE_BUILD_TYPE=Release `
  -DMODERNGEKKO_ENABLE_DOLPHIN_RUNTIME=ON `
  -DMODERNGEKKO_FRONTEND_NAME="My Recomp" `
  -DMODERNGEKKO_LAUNCHER_OUTPUT_NAME="MyRecomp" `
  -DMODERNGEKKO_RUNNER_OUTPUT_NAME="MyRecompRunner" `
  -DMODERNGEKKO_USER_DIRECTORY_NAME="MyRecomp" `
  -DMODERNGEKKO_DEFAULT_WINDOW_TITLE="My Game" `
  -DMODERNGEKKO_REQUIRED_DISC_ID="DISCID" `
  -DMODERNGEKKO_REQUIRED_DOL_SHA256="<retail-dol-sha256>" `
  -DMODERNGEKKO_PORTABLE_DEFAULT_GAME=ON `
  -DMODERNGEKKO_GAMECUBE_CONTROLLERS=ON
```

Optional:

- `MODERNGEKKO_GAME_SETTINGS_OVERRIDE` copies a game INI (e.g. the idle-loop
  setting) into `Sys/GameSettings`.
- `MODERNGEKKO_DOL_PATCH_MANIFEST` applies a native DOL patch manifest.
- `MODERNGEKKO_REQUIRED_REL_SHA256` / `MODERNGEKKO_REQUIRED_ASSETS_SHA256` for
  games with REL modules/assets.

Build:

```powershell
cmake --build build\moderngekko --target moderngekko-run moderngekko-launcher -j 8
```

### Build from a short path

`moderngekko-port build` writes its module cache under
`<output>\<DISC-ID>\<dol-sha>-<toolchain-hash>\`. Long project names with
spaces push the MSVC object path past the 250-character limit and the build
fails inside the object writer, not with a clear "path too long" message.

Build from a short output root and copy the DLL back:

```powershell
moderngekko-port.exe build work\game --backend c --toolchain clang --opt-level 3 --output C:\mygame\modules
copy /Y C:\mygame\modules\DISCID\<cache>\gDISCID_recomp.dll build\gDISCID_recomp.dll
```

The `<toolchain-hash>` part of the cache key changes with the compiler version,
so two modules built with different Clang/MSVC installs land in different
folders even from the same DOL. Keep the path and the hash in `STATE.md`; it is
how you tell which DLL is actually loaded.

## 1. Generate the C

```powershell
$env:Path = "C:\path\to\ninja;" + $env:Path
cmd /c '"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul && ^
  build\moderngekko\moderngekko-port.exe build work\game --backend c --toolchain msvc --output build\modules'
```

Output for one game:

```text
build/modules/<ID>/<disc-sha>-<hash>/
  dolrecomp-output/generated/
    generated.c
    generated.h
    generated_smc.txt
    chunks/chunk_XXXX_text1_XXXXXXXX.c
  module-build/             CMake project generated for the C module
  module-pgogen/            instrumented build
  module-pgo/               profile-use build
```

`generated_smc.txt` lists the ranges containing possible patching
instructions. Keep it with the module metadata.

## 2. Compile flags that matter

Start from the shipped PGO module build:

```text
-march=x86-64-v3 -mtune=generic
-DDOLRECOMP_C_LOOP_CYCLE_BUDGET=4096
-DDOLRECOMP_C_MAX_CALL_DEPTH=128
-O3 -DNDEBUG -std=gnu11
-flto=thin
-ffp-contract=off -fno-fast-math
-fprofile-use=<merged.profdata>
```

Why:

- **Clang** is dramatically faster than MSVC for the generated C. In the
  SpongeBob living-room test, MSVC `/O2` was 27.8 fps; Clang `-O3` was 46.8.
- **ThinLTO** lets cross-chunk calls inline without a full-LTO memory bill.
- **`x86-64-v3`** is the portable AVX2 baseline. `-march=native` is faster on
  the build machine (52.6 vs 49.9 fps in one test) but will not run on older
  CPUs. Ship `x86-64-v3`, or ship a separate native module with runtime
  selection.
- **Loop budget 4096 / call depth 128** was the fastest tested pair. Larger
  loop budgets stop helping and can hurt I-cache; larger call depth regressed.
- **`-ffp-contract=off -fno-fast-math`** preserves Gekko FP semantics. Do not
  enable fast-math just to gain a few percent; it changes rounding and
  exception behavior.
- **PGO** is the difference between a 50 fps module and a 59-60 fps module.
  Collect it on **gameplay**, not only the title screen.

### Verify the defines actually reached the compiler

The generated header defaults are:

```c
#define DOLRECOMP_C_LOOP_CYCLE_BUDGET 256
#define DOLRECOMP_C_MAX_CALL_DEPTH 24
```

Shipping modules want `4096` / `128`, but a build script can look correct and
still use the defaults. One project produced several PGO modules this way and
only noticed when it diffed against a known-good `CMakeCache.txt`. Check the
real build files, not the docs:

```powershell
Select-String -Path build\modules\...\module-pgo\CMakeCache.txt -Pattern 'DOLRECOMP_C_'
Select-String -Path build\modules\...\module-pgo\build.ninja -Pattern 'DOLRECOMP_C_'
```

The compiled flags should also show all of `-O3`, `-flto=thin`,
`-fvisibility=hidden`, `-ffp-contract=off` and `-fno-fast-math`. If `-march`
or the defines are missing, the module is not the build you think it is.

## 3. PGO recipe

Build an instrumented module (`-fprofile-generate`), run a representative
gameplay segment, then rebuild with `-fprofile-use`.

```powershell
# 1. instrumented module
cmake -S <pgogen-src> -B <pgogen-build> -G Ninja `
  -DCMAKE_C_COMPILER="C:\Program Files\LLVM\bin\clang.exe" `
  -DCMAKE_C_FLAGS="-march=x86-64-v3 -mtune=generic -O3 -DNDEBUG -std=gnu11 -flto=thin -fprofile-generate=<dir>"
cmake --build <pgogen-build> -j 8

# 2. run gameplay with the instrumented module
$env:LLVM_PROFILE_FILE="<dir>\play-%p.profraw"
runner --game work\game --module <pgogen>\g<ID>_recomp.dll `
  --user-dir work\pgo-user --load-state <gameplay.state> `
  --graphics Vulkan --audio Null --allow-interpreter
# stop gracefully (automation command=stop) so the profile flushes

# 3. merge
llvm-profdata merge -o <dir>\merged.profdata <dir>\*.profraw

# 4. profile-use rebuild
cmake -S <pgo-src> -B <pgo-build> -G Ninja `
  -DCMAKE_C_COMPILER="C:\Program Files\LLVM\bin\clang.exe" `
  -DCMAKE_C_FLAGS="-march=x86-64-v3 -mtune=generic -O3 -DNDEBUG -std=gnu11 -flto=thin -fprofile-use=<dir>\merged.profdata -Wno-profile-instr-out-of-date -Wno-profile-instr-unprofiled"
cmake --build <pgo-build> -j 8
```

Collect the profile across several areas and states, not one room. A profile
from the title screen will optimize the wrong code. If the game has a frame
limiter, the idle loop will dominate the profile; that is expected and is a
reason to use the idle-skip setting.

Keep **separate boot and play profiles** and merge both. Boot/loading code
(asset streaming, shader setup, first-frame initialization) and steady-state
gameplay have almost disjoint hot sets; a play-only profile can leave the
load path unoptimized and a boot-only profile optimizes the wrong half.

```powershell
$env:LLVM_PROFILE_FILE="work\pgo\boot-%p.profraw"
runner ... --graphics Vulkan --audio Null
$env:LLVM_PROFILE_FILE="work\pgo\play-%p.profraw"
runner ... --load-state work\gameplay.state ...
llvm-profdata merge -o work\pgo\merged.profdata work\pgo\boot-*.profraw work\pgo\play-*.profraw
```

A nonzero training-run exit does **not** mean the profile is dead. One PGO run
exited `0xC000001D` while the game window was closing, so the build helper
refused to merge it, but the `.profraw` had already flushed and merged into a
valid 1,197-function profile. Check the file before throwing the run away:

```powershell
llvm-profdata show --all-functions --counts work\pgo\boot-*.profraw | Select-Object -First 20
```

Sanity numbers from a real profile (RPBB): 1,197 functions, 704,004 blocks,
maximum function count ~973 million, maximum internal block count ~2.2 billion.
A profile with a handful of functions or a tiny total count is a bad capture.

Inspect the profile:

```powershell
llvm-profdata show --topn=60 --counts merged.profdata
```

Function names include generated chunk paths and runtime helpers. Use the
counts to find hot generated functions and hot helper calls (`ppc_cache_control`,
`ni_mul`, `fp_write_single`, `ppc_host_call`, `ppc_mftb`); combine with the
dispatch sample PC list before editing code.

## 4. DolRecomp patches that are worth checking

### Cache-op emission

Older C output emitted `ppc_fallback_instruction(...); return;` for every
`dcbf`/`dcbst`/`dcbi`/`icbi`. Streaming code flushes caches in 32-byte loops,
so this creates millions of fallbacks and kills the native burst. The emitter
should call `ppc_cache_control(ctx, operation, ea, cia);` inline and continue.
The runtime's fast path reads the two GPRs and changes no CPU state.

SpongeBob result: 33 million fallbacks in one run -> ~18,000; 46.8 -> 49.9 fps.

### Cross-chunk direct calls

The C backend has a direct-call path, but it is dead if `emit_set_chunk_table`
is never called: every cross-chunk `bl` becomes `ctx->pc = target; return;`
and goes back through the chassis/dispatcher, two state syncs and a downcount
flush.

Fix: initialize the global chunk table during module init. The generated module
then has tens of thousands of direct call sites (SpongeBob: ~36,000).

SpongeBob result: intro/logo movie 0.41x -> 1.00x, living room 54.6 -> 59.7 fps,
movie audio dropouts -> continuous.

### Generated-code invariants

- Keep the `ctx->pc` materialization policy. It is needed before calls,
  exceptions, memory faults and dispatcher returns; removing it blindly breaks
  error PCs.
- Cache ops must remain ordered with memory operations.
- Do not change FP contraction/fast-math to chase speed.
- Regenerate after emitter changes; never hand-edit generated C.

## 5. Module metadata and validation

The runner should require:

- disc ID
- retail `main.dol` SHA-256
- optional REL/asset hashes if the game uses them
- module ABI version and entry point

Run `moderngekko-port inspect work\game` (or the template's equivalent) before
the first boot. It reports the disc ID, entry point and DOL hash from the
extracted tree, so a wrong extraction fails here instead of at module load.

Inspect can also fail for a non-obvious reason: a `std::filesystem`
`generic_string()` call throws on file names that are not representable in the
ANSI codepage, and the exception reaches `std::terminate`/`abort()` (exit
`0xC0000409`). Retail discs do ship Shift-JIS developer files. Sort with
`lexically_relative()` and build names with `generic_u8string()`. See
[09-troubleshooting.md](09-troubleshooting.md#build-and-extraction).

At boot, verify `[staticrecomp] module loaded: ... entry=0x...` and that the
module's code ranges/SMC tables are populated. `fallback=0`, `smc_failed=0`
and `hook_fb` small are the healthy baseline. A high `native_exc` count is a
red flag: inspect the game code/exception path, not just FPS.

## 6. Module build acceptance

- [ ] Generated C is reproducible from the retail DOL.
- [ ] `generated_smc.txt` retained.
- [ ] PGO profile from real gameplay, not just boot.
- [ ] Module loads and boots from a save state.
- [ ] No fallback instructions or SMC hash failures in the steady state.
- [ ] Benchmark before/after recorded.
