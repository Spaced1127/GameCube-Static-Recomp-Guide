# New project checklist

## Inputs

- [ ] Legally dumped GameCube disc (ISO or RVZ).
- [ ] Disc ID, region, revision.
- [ ] Redump size/CRC-32.
- [ ] `main.dol` SHA-256.
- [ ] GameCube controller mapping / keyboard fallback.

## Project

- [ ] ModernGekko/Dolphin template copied and configured.
- [ ] Project name/output names set.
- [ ] `tools/` copied.
- [ ] `docs/release/` README/manifest placeholders.
- [ ] `.gitignore` excludes game data/builds/states.

## Build

- [ ] Build tree configured (CMake/Ninja/MSVC).
- [ ] `moderngekko-port` generates C.
- [ ] Module compiles with Clang + PGO.
- [ ] Runner/launcher build.
- [ ] Module metadata has disc ID/DOL hash/entry point.

## First boot

- [ ] `module loaded` in log.
- [ ] `fallback=0`, `smc_failed=0`.
- [ ] Legal/title screens render (EFB access).
- [ ] Controller detected.
- [ ] Save state loaded.
- [ ] Audio backend chosen.

## Host setup

- [ ] `<user-dir>\Cache\Shaders` created by the launcher.
- [ ] Affinity pinned to physical cores on SMT CPUs; `High` priority.
- [ ] `Sys/GC/dsp_rom.bin` and `dsp_coef.bin` next to the runner.
- [ ] Shader/pipeline cache written after a run.
- [ ] Windows per-app mixer checked if audio is silent.
- [ ] State ladder captured (title, menu, select, in-game).
- [ ] Automation input verified (pad taps, first command after load-state sent
      twice).

## Performance

- [ ] Baseline low/high.
- [ ] JIT reference.
- [ ] Profile/PGO.
- [ ] Idle loop if applicable.
- [ ] Core decision: static / JIT default / both.
- [ ] Frame cap at 59.94 Hz.

## Launcher parity and theme

- [ ] Launcher built from the shared shell, not a per-title copy.
- [ ] Parity features present: setup, settings, input, states, cards, host
      checks, logs, updates, clean close.
- [ ] Theme applied: product/exe names, launcher badge, runner cover, accent,
      strings, manifest labels.
- [ ] No other title's name, icon or disc ID in the build or manifest.
- [ ] Theme needed no code change; any missing feature went into the shell.
- [ ] Custom launcher and manifest use the same user dir, module and config
      paths.

## Packaging

- [ ] RecompLauncher manifest.
- [ ] Prepare progress.
- [ ] Settings/config.
- [ ] Saves/logs/exit codes.
- [ ] Icons.
- [ ] README/CHANGELOG/release notes.
- [ ] No game data scan.
- [ ] Release asset hash/back-download check.
