# 00 - Quick start

This is the shortest path from a retail GameCube disc to a tested Windows
build. Substitute your own project name, disc ID and paths.

## 0. Prerequisites

- Windows 10/11 x64 for the shipped build.
- Visual Studio Build Tools with the MSVC x64 toolchain and Windows SDK.
- LLVM/Clang and `lld-link` on `PATH`.
- CMake 3.24+ and Ninja.
- Python 3 for the disc/DOL helpers in `tools/`.
- Optional: Dolphin (for a JIT reference, disc conversion and state
  inspection), 7-Zip, Git, `gh`.
- Your own legally dumped GameCube disc (ISO or RVZ). No game data is
  distributed with the project.

## 1. Create the project skeleton

```text
MyRecomp/
  lib/ModernGekko-Template/     runtime + DolRecomp template
  work/disc/                    your disc image (git-ignored)
  work/game/                    extracted sys/ + files/ (git-ignored)
  build/moderngekko/            CMake build tree
  build/modules/                generated + compiled modules
  tools/                        disc/DOL/release helpers
  docs/release/                 README.txt, recomplauncher.json
  dist/                         release folders/zips (git-ignored)
```

Copy the ModernGekko template into `lib/`, then configure/build it with the
project name/disc ID. Keep the build tree; do not clean it between changes.

## 2. Verify and extract the disc

```powershell
python tools/gcdisc.py info work\disc\game.iso
python tools\gcdisc.py extract work\disc\game.iso work\game
python tools\gcdisc.py dol work\disc\game.iso work\game
python tools\verify_dol.py work\disc\game.iso work\game\sys\main.dol
```

Record:

- disc ID (e.g. `GSQE78`)
- `main.dol` SHA-256
- Redump size and CRC-32
- region and revision

If the dump is RVZ:

```powershell
python tools\rvz_extract.py work\disc\game.rvz work\disc\game.iso
```

Then re-run the commands above. See [02-disc-and-dol.md](02-disc-and-dol.md).

## 3. Generate the static C module

The template's `moderngekko-port` tool emits the generated C and a CMake
project for the module:

```powershell
$env:Path = "C:\path\to\ninja;" + $env:Path
cmd /c '"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul && ^
  build\moderngekko\moderngekko-port.exe build work\game --backend c --toolchain msvc --output build\modules'
```

This creates a `generated/chunks/*.c` tree plus `generated.c`,
`generated.h`, `module_tables.inc` and `generated_smc.txt` under
`build/modules/<ID>/...`. Inspect `generated_smc.txt` for known patch points.

## 4. Compile the module

Use Clang, not MSVC, for the generated C. Start with the shipped flags and
collect PGO on real gameplay:

```text
-march=x86-64-v3 -mtune=generic
-DDOLRECOMP_C_LOOP_CYCLE_BUDGET=4096
-DDOLRECOMP_C_MAX_CALL_DEPTH=128
-O3 -DNDEBUG -std=gnu11
-flto=thin
-ffp-contract=off -fno-fast-math
-fprofile-use=<merged.profdata>
```

The exact CMake/Ninja flow and PGO recipe are in
[03-build-static-module.md](03-build-static-module.md). The output is
`g<ID>_recomp.dll` plus an import library.

## 5. First boot

```powershell
SpongeBobRecompRunner.exe --game work\game --module build\modules\...\gGSQE78_recomp.dll `
  --user-dir work\user --graphics Vulkan --audio Null --allow-interpreter
```

Check the log:

```text
[staticrecomp] core init
[staticrecomp] module loaded: ... entry=0x80003140
[staticrecomp] SMC: chunk ... accepted data-only write
[staticrecomp] shutdown: native=... fallback=0 native_exc=... hook_fb=... smc_failed=0
```

`fallback=0`, `smc_failed=0` and a small `hook_fb` are good signs. `fallback`
or `SMC hash mismatch` means the emitter/runtime is missing something.

Use `--load-state <state.sav>` for deterministic testing. Create states with
the automation protocol (see [06-debugging-and-testing.md](06-debugging-and-testing.md)).

## 6. Baseline performance

Measure with the same state and settings:

| Run | Settings | What it tells you |
|---|---|---|
| Low | 1x, no MSAA/SSAA, AF 0 | CPU ceiling |
| High | shipped settings | real-world result |
| JIT | `--core jit` or `MODERNGEKKO_STATICRECOMP=0` | runtime/CPU reference |

If low and high are nearly the same, the static module is CPU-bound. Do not
lower GPU settings further. Go to [05-performance.md](05-performance.md) and
[11-agent-playbook.md](11-agent-playbook.md).

## 7. Choose the playable core

- **Static is close to 60** -> keep static, use PGO/idle-loop/codegen tuning.
- **Static is far below 60 but JIT holds 60** -> make JIT the default playable
  path and keep the static module as a selectable artifact. This is what the
  Rocket Power project does and what SpongeBob v0.1.3 does.

The runtime already supports both:

```text
MODERNGEKKO_STATICRECOMP=0   # JIT core
--core jit                   # JIT, skip static module discovery
--core static                # static module
```

## 8. Cap the frame rate

The GameCube VI is **59.94 Hz**. Clamp `emulation_speed` to `1.0`; do not ship
150%, 200% or unlocked options. Old configs should load at 60, not fail.

## 9. RecompLauncher

Add a top-level `recomplauncher.json` to every release zip. Minimum viable
manifest:

- `game.kind`
- `game.label`
- `game.dumps` (Redump size/CRC-32)
- `prepare` (headless extract, `progress` lines)
- `start` (runner + `--core`)
- `config` / `settings`
- `saves` / `folders` / `actions`

Use [templates/recomplauncher.template.json](../templates/recomplauncher.template.json)
and read [07-recomplauncher.md](07-recomplauncher.md). Validate it against the
official schema before shipping.

The manifest and the custom launcher are one product: same user dir, module and
config paths, same feature set. The launcher is themed per title, never forked;
see [15-launcher-parity.md](15-launcher-parity.md#the-launcher-parity-contract).

## 10. Icons and release

- Embed multi-size `.ico` files in both executables with a Windows RC resource
  (see [08-icons-and-release.md](08-icons-and-release.md)).
- Theme the shared launcher for this title: names, icons, accent, strings,
  manifest labels. Run the parity table in
  [15-launcher-parity.md](15-launcher-parity.md#the-launcher-parity-contract).
- Package `Name-vX.Y.Z-Windows-x64.zip` with the manifest at the top.
- Scan for game data.
- Compute SHA-256, publish, download it back, verify the hash, schema,
  contents, icons and absence of game data.

## Minimum acceptance check

- [ ] Build succeeds from documented commands.
- [ ] Runner boots to gameplay from a real save state.
- [ ] Log shows `fallback=0`, `smc_failed=0`, no new exceptions.
- [ ] Target FPS holds (usually 59.94).
- [ ] Settings/saves/logs work.
- [ ] RecompLauncher manifest validates and setup reaches "Ready to play".
- [ ] Launcher parity table passed; theme is this title only.
- [ ] Release contains no game data.
- [ ] User approved commit/publish.
