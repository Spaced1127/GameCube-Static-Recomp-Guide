# GameCube Static Recomp Guide

A practical, battle-tested reference for turning a retail GameCube `main.dol`
into a native Windows port with **DolRecomp**, a **ModernGekko/Dolphin-derived
runtime**, and **RecompLauncher** packaging.

This guide was assembled from five working projects:

- **SpongeBob SquarePants: Revenge of the Flying Dutchman** (`GSQE78`)
  <https://github.com/Spaced1127/SpongeBobRecomp>
- **Rocket Power: Beach Bandits** (`GBQE78`)
  <https://github.com/Spaced1127/RPBB-Static-Recomp>
- **Aggressive Inline** (`GILE51`)
  <https://github.com/Spaced1127/Aggressive-Inline-Static-Recomp>
- **WWE WrestleMania X8** (`GW3E78`) and **WWE WrestleMania XIX** (`GW9E78`)
- The Rocket Power decomp, asset-format and Switch experiments, which informed
  the asset and secondary-target chapters

No game data, disc images, DOL files, textures, audio, or cover art are
included in this repository. Every project still requires the player's own
legally dumped disc.

## Start here

| If you are... | Read |
|---|---|
| Starting a new GameCube recomp | [docs/00-quickstart.md](docs/00-quickstart.md), [checklists/NEW-PROJECT.md](checklists/NEW-PROJECT.md) |
| Trying to understand the code path | [docs/01-architecture.md](docs/01-architecture.md) |
| Handling the disc, DOL and FST | [docs/02-disc-and-dol.md](docs/02-disc-and-dol.md) |
| Building the static module | [docs/03-build-static-module.md](docs/03-build-static-module.md) |
| Wiring the runtime and launcher | [docs/04-runtime-and-launcher.md](docs/04-runtime-and-launcher.md) |
| Chasing frame-rate dips | [docs/05-performance.md](docs/05-performance.md), [checklists/PERFORMANCE.md](checklists/PERFORMANCE.md) |
| Debugging or automating tests | [docs/06-debugging-and-testing.md](docs/06-debugging-and-testing.md) |
| Shipping through RecompLauncher | [docs/07-recomplauncher.md](docs/07-recomplauncher.md) |
| Adding icons and cutting a release | [docs/08-icons-and-release.md](docs/08-icons-and-release.md), [checklists/RELEASE.md](checklists/RELEASE.md) |
| Stuck on a failure | [docs/09-troubleshooting.md](docs/09-troubleshooting.md) |
| Working with the game's archives, textures, meshes or levels | [docs/12-asset-formats.md](docs/12-asset-formats.md) |
| Shipping to a handheld, console or secondary target | [docs/13-other-targets.md](docs/13-other-targets.md) |
| An AI agent picking up the work | [AGENTS.md](AGENTS.md), [docs/11-agent-playbook.md](docs/11-agent-playbook.md) |
| Just need the commands | [docs/CHEATSHEET.md](docs/CHEATSHEET.md) |

## The short version

1. **Verify the disc.** Extract the DOL, record the disc ID, DOL SHA-256, and
   Redump size/CRC-32. Keep all game data out of Git.
2. **Generate C.** Run DolRecomp's C backend over `main.dol`. Fix cache-op
   emission and cross-chunk direct calls before tuning performance.
3. **Compile the module.** Clang `-O3`, ThinLTO, `x86-64-v3`, loop budget
   `4096`, call depth `128`, PGO on real gameplay.
4. **Boot the runtime.** `runner --game <Game> --module <dll> --user-dir <dir>`.
   Confirm the module loads, no fallback instructions, no SMC hash failures.
5. **Baseline CPU vs GPU.** Drop to 1x/no AA. If FPS barely moves, it is CPU;
   if it jumps, it is GPU. Fix the host first: pin to physical cores, create
   `Cache\Shaders`, warm the pipeline cache, and check the app is not muted.
6. **Profile.** Use PGO block counts and
   `STATICRECOMP_DISPATCH_SAMPLES=1`. Look for the frame-limiter loop, FP
   helpers, cache control, host calls, and GX FIFO traffic.
7. **Choose the right core.** A static module is not always the fastest
   playable path. Dolphin's JIT is a legitimate default when the static module
   is CPU-limited; keep the static module as a selectable artifact.
8. **Cap at the console rate.** The GameCube VI is 59.94 Hz. Do not expose
   frame-rate uncapping; clamp speed to 1.0.
9. **Package for RecompLauncher.** Top-level `recomplauncher.json`, verified
   Redump dump, headless `prepare` with `progress` lines, settings, saves/logs.
10. **Verify the actual artifact.** Download the release back, check the hash,
    schema, contents, icons, and that no game data leaked.

## Golden rules

- **Never commit or publish game data.** No ISO/RVZ/WBFS/GCM, DOL, FST,
    `Game/`, textures, audio, saves, or cover art.
- **Never claim a fix without a real run.** Build, launch, load a save state,
    read `status.txt`, and inspect the log.
- **Do not clean the build tree** unless you must. A cold DolRecomp/Dolphin
    build is expensive; generated chunks and PGO data are valuable.
- **Do not edit generated C** and call it fixed. Fix the emitter or the
    runtime, then regenerate.
- **Measure before optimizing.** Lower the GPU load first; a CPU bottleneck
    will not move. Then check the host: affinity, shader cache, foreground load.
- **A release must be built from the runner you tested.** A stale runner
  silently ignores new settings; prove the option reached the runtime from the
  `[video]` log line.
- **A 59.9 title is full speed.** The VI runs at 59.94 Hz; the target is 59.94,
    not 60.000.
- **External load is real.** A local LLM, browser, or compositor using the GPU
    can make a maxed MSAA/SSAA profile dip even when the port is fine.
- **Fullscreen belongs to the window.** Create the window windowed, initialize
    the video backend, then apply borderless fullscreen after boot. Do not
    toggle it in the platform destructor, and validate the swap-chain image
    before every present. See
    [docs/04](docs/04-runtime-and-launcher.md#fullscreen-and-shutdown-windows).
- **Same tag, new asset is not an update.** If you replace a GitHub release
    without bumping the tag, existing RecompLauncher installs will not see it.
    Use a new version for real updates.
- **Ask before committing or publishing.** Code changes and release actions are
    separate decisions.

## Repository map

```text
README.md                     this page
AGENTS.md                     rules for AI agents working in a recomp
docs/00-quickstart.md         new-project path and minimum commands
docs/CHEATSHEET.md            copy-paste commands for every phase
docs/01-architecture.md       disc -> module -> runtime -> launcher
docs/02-disc-and-dol.md       GameCube disc/DOL/FST, Redump, extraction
docs/03-build-static-module.md DolRecomp C, Clang, PGO, patches
docs/04-runtime-and-launcher.md runner/launcher, config, CPU core, idle loop
docs/05-performance.md        benchmark method, measured results, optimization catalog
docs/06-debugging-and-testing.md logs, automation, save states, dispatch samples
docs/07-recomplauncher.md     SDK levels, manifest, settings, prepare, dumps
docs/08-icons-and-release.md  ICO/RC embedding, packaging, release verification
docs/09-troubleshooting.md    symptom -> cause -> fix
docs/10-case-studies.md       five ports, with numbers and the bugs that mattered
docs/11-agent-playbook.md     ordered playbook for an AI agent
docs/12-asset-formats.md      archive/texture/mesh/level formats and validation
docs/13-other-targets.md      handheld/console paths, honest port labelling
docs/appendix/                raw SpongeBob performance/test/state notes
docs/recomplauncher.schema.json  offline copy of the SDK schema
templates/                    manifest, RC/icon, PGO, release, automation, AGENTS
tools/                        generic disc/DOL/RVZ helpers used by both projects
examples/                     real RecompLauncher manifests (no game data)
checklists/                   new project, performance, release
```

## What actually moved the needle

From the SpongeBob project, in order of impact:

1. **Clang instead of MSVC** for the generated C: 27.8 -> 46.8 fps in the
   living-room test.
2. **Cache-op codegen fix** (no fallback/return for `dcbf`/`dcbst`/`dcbi`/
   `icbi`): 46.8 -> 49.9 fps; fallbacks fell from 33 million to ~18,000.
3. **`-march=native`** on the build machine: 52.6 fps; ship an `x86-64-v3`
   build for portability, or ship a native module separately.
4. **Loop budget 2048/4096 + call depth 128**: 56-59 fps.
5. **PGO on real gameplay**: ~57-60 fps, with the final build holding 59-60.5
   in the living room.
6. **Cross-chunk direct calls**: intro movies 0.41x -> 1.00x; living room
   54.6 -> 59.7 fps.
7. **Idle-loop skip** (`StaticRecompIdlePC`): removes the frame-limiter spin.
   Low settings 61 -> 72 fps; high 1080p 61.9 -> 67.7 fps uncapped.
8. **JIT default** when the static module is CPU-limited outdoors: the same
   Bikini Bottom save is 42.1 fps static and 59.94 fps JIT. The Rocket Power
   release uses the same split.

Across the later ports:

1. **Host setup before codegen.** Pinning to physical cores (47.7 -> 58.5 fps on
   Rocket Power) and creating `Cache\Shaders` removed two "codegen" symptoms
   without touching the module.
2. **Clang holds the console rate in-match.** WrestleMania X8: 40.7 fps MSVC vs
   59.94 fps Clang on the same save state. Aggressive Inline: 59.9 fps at 3x
   native with the GPU at 2-3 ms.
3. **Rebuild the runner with the settings.** A stale runner made widescreen look
   broken; the `[video] aspect=... widescreen=...` line is the proof.
4. **PGO only counts if the defines are real.** Several modules had run at the
   generated defaults (256/24) while the docs said 4096/128.
5. **Fix the hash walk, not the disc.** Two Shift-JIS PSD names crashed
   `inspect` and the runner with `0xC0000409`.
6. **Rumble belongs on its own thread.** Controller writes on the CPU thread
   caused a landing/collision stutter in Rocket Power.
7. **Verify controller mappings on the game's menus.** WMX8's D-pad is a taunt,
   not movement; the menus only read the main stick.

The full tables and method are in [docs/05-performance.md](docs/05-performance.md).

## External references

- DolRecomp: <https://github.com/ExpansionPak/DolRecomp>
- Dolphin (runtime base): <https://github.com/dolphin-emu/dolphin>
- ModernGekko runtime: <https://github.com/ExpansionPak/ModernGekko>
- ModernGekko template: <https://github.com/ExpansionPak/ModernGekko-Template>
- RecompLauncher: <https://recomplauncher.com>
- RecompLauncher SDK guide:
  <https://recomplauncher.com/sdk-files/guide.md>
- RecompLauncher schema:
  <https://recomplauncher.com/schema/recomplauncher.json>
- Redump: <http://redump.org>
- GameTDB: <https://www.gametdb.com>
- LLVM PGO: <https://llvm.org/docs/CommandGuide/llvm-profdata.html>
- CMake `enable_language` (RC): <https://cmake.org/cmake/help/latest/command/enable_language.html>

## License

The guide and project scripts are distributed under the **GNU General Public
License v3.0**; see [LICENSE](LICENSE). Dolphin is GPLv2+ (aggregate GPLv3),
DolRecomp is GPLv3, and third-party tools keep their own licenses.
