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

## Performance

- [ ] Baseline low/high.
- [ ] JIT reference.
- [ ] Profile/PGO.
- [ ] Idle loop if applicable.
- [ ] Core decision: static / JIT default / both.
- [ ] Frame cap at 59.94 Hz.

## Packaging

- [ ] RecompLauncher manifest.
- [ ] Prepare progress.
- [ ] Settings/config.
- [ ] Saves/logs/exit codes.
- [ ] Icons.
- [ ] README/CHANGELOG/release notes.
- [ ] No game data scan.
- [ ] Release asset hash/back-download check.
