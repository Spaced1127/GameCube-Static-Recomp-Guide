# 11 - Agent playbook

This is the ordered playbook for an AI agent asked to build, fix or ship a
GameCube static recomp. Follow it in order; do not skip the baseline.

## Phase 0 - Read and restate

1. Read the target project's `STATE.md`, `AGENTS.md`, build scripts and latest
   log.
2. Restate the goal, the known-good state and the first failing change.
3. Identify the game/disc ID, DOL hash, module path, runtime and release tag.
4. Ask for a save state/log/disc if the request cannot be reproduced.

## Phase 1 - Inventory

- [ ] Disc ID, region, revision, Redump size/CRC.
- [ ] `main.dol` SHA-256, entry point.
- [ ] Extracted `Game/sys` and `Game/files`.
- [ ] Build tree, module DLL, PGO profile.
- [ ] Launcher/runner paths, config, `default-game.txt`.
- [ ] Current core (static/JIT), settings, save state.
- [ ] Git/release state; do not commit/publish yet.

## Phase 2 - Reproduce

- [ ] Build with the documented command.
- [ ] Run from a real save state with a fixed config.
- [ ] Capture `status.txt`, log tail, screenshot.
- [ ] Confirm the reported symptom with numbers.
- [ ] Record baseline before changing anything.

## Phase 3 - Classify

### Boot failure

- module missing -> path/name/`--module`
- disc/DOL mismatch -> verify hash/region
- `allow_interpreter` -> JIT mode
- black 2D -> EFB access
- SMC/fallback -> emitter/runtime
- `0xC0000409` from `inspect`/boot -> non-ASCII file names in the extracted
  tree (`generic_string()` throw -> `__fastfail`)
- no DSP init -> `Sys/GC/dsp_rom.bin` + `dsp_coef.bin` missing
- settings ignored -> stale runner binary, not the config parser

### Performance

0. Fix the host: physical-core affinity, `Cache\Shaders`, warm cache, unmuted
   app, closed background load.
1. Low (1x/no AA) vs high.
2. Static vs JIT.
3. External GPU/CPU load.
4. PGO counts + dispatch samples.
5. Idle loop? Check the hottest dispatch PC and the generated loop.
6. FP/cache/host call helpers hot? Use the optimization catalog.

### Packaging

- manifest location/schema
- prepare progress/exit code
- start command/args/env
- config path/keys
- dumps/RVZ/check
- no game data

### Secondary target

- Which path is this: Dolphin-derived runtime (emulator port), cross-compiled
  static module, or from-scratch viewer?
- Is the emulation speed limit 100%? A 90% limit looks like a CPU bottleneck.
- Was the clock profile verified while the game ran, and on the right title ID?
- Is the release labelled honestly ("runs the retail game on an emulator port",
  not "native port")?

### Fullscreen / shutdown

- Is the window created windowed, with borderless fullscreen applied after the
  video backend initializes? Fix that first if not.
- Does `~PlatformWin32()` call `ToggleFullscreen()`? Remove it; destroy the
  borderless window directly.
- Does `VKGfx::BindBackbuffer()` check the current texture and framebuffer?
  Does `IsCurrentImageValid()` check index/texture/framebuffer? Add both.
- Does `ResizeSwapChain()`/`RecreateSwapChain()` call `PanicAlertFmt()`? Log
  and return `false` instead; a modal dialog during close looks like a hang.
- Does one ALT+F4 exit? Add a 3-second power-button grace deadline.
- Repro: fullscreen close, F11 leave/re-enter then close, close after a save,
  windowed close, double-close.

## Phase 4 - Change one thing

- Keep the diff small and explain the expected effect.
- Prefer runtime/emitter fixes over generated-code edits.
- For performance, change one variable and rerun the same state.
- For packaging, change one field and validate/run the UI.

## Phase 5 - Verify

- Build passes.
- Same state boots.
- `fallback=0`, `smc_failed=0`, no new exceptions.
- Target FPS/metadata met.
- Fullscreen ALT+F4, F11 toggle, windowed close and close-after-save exit
  cleanly; no crash dump or hidden dialog.
- RecompLauncher setup/settings/Play verified if packaging.
- Release downloaded back and checked if publishing.

## Phase 6 - Report

Include:

- what was wrong, with evidence
- what changed, with file paths
- before/after numbers
- what was not tested/limitations
- whether anything was committed/published

## Performance decision tree

```text
FPS below target?
  |
  +-- Low settings much faster? -> GPU-bound
  |     lower MSAA/SSAA/resolution; check driver/external load
  |
  +-- Low settings ~same? -> CPU-bound
        |
        +-- JIT holds target?
        |     yes -> ship JIT default, static optional
        |     no  -> runtime/GPU/CPU issue; profile
        |
        +-- Static close (<10% short)?
              PGO, codegen, idle loop, helper fast paths
```

## Commit/publish policy

- Code edits are not permission to commit.
- A commit is not permission to tag/release.
- A release is not permission to replace a tag.
- Ask explicitly for each public step.
- If you accidentally publish, say so immediately and stop.

## Context and state

- Keep `STATE.md` current: disc/build/runtime/performance/open issues/release.
- Keep a ledger of decisions and measurements for long runs.
- Do not rely on chat history for critical numbers; write them to the project.
- If context is long/stale, move to a fresh session that reads `STATE.md` and
  the relevant docs only.

## Definition of done

- Build from documented commands.
- Boot to gameplay from a real state.
- Target performance holds; limitation documented if not.
- RecompLauncher manifest validates; setup/settings/Play verified.
- No game data in repo/release.
- User approved public actions.
