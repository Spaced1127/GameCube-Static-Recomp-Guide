# 06 - Debugging and testing

## Logs and stats

Runner stderr/log:

```text
[video] backend=Vulkan scale=3 msaa=8 ssaa=0 af=4 vsync=1 aspect=1 widescreen=0 fullscreen=0
[audio] mute=0 volume=25
[staticrecomp] core init
[staticrecomp] module loaded: ... entry=0x80003140
[staticrecomp] SMC: chunk ... accepted data-only write
[staticrecomp] shutdown: native=... fallback=0 native_exc=... hook_fb=... smc_failed=0 verifications=... reverify_events=... bursts=... cycles=...
```

- `fallback`: instructions that went to the interpreter/JIT fallback. Should be
  0 in the steady state. Hundreds/thousands means unmodeled instructions.
- `native_exc`: exceptions raised by the module. A few thousand over a run can
  be normal for OS calls; hundreds of thousands per second is a red flag.
- `hook_fb`: framebuffer/EFB hooks; watch for runaway counts.
- `smc_failed`: self-modifying-code chunks that failed hash verification.
- `verifications`/`reverify_events`: SMC verification activity.
- `bursts`/`cycles`: native dispatch and guest-cycle counters.

`[staticrecomp] SMC: chunk ... accepted data-only write` is healthy. `hash
mismatch; interpreter until next invalidation` means code changed and the
runtime correctly fell back; repeated mismatches point at a cache-op/SMC bug.

## Automation protocol

Start the runner with `--automation-dir <dir>`. The runner creates
`<dir>/status.txt` and reads command files from `<dir>/commands/`.

Command file content (any filename, `.txt` recommended):

```text
command=pad_frames
port=0
frames=90
main_y=1
```

```text
command=screenshot
path=C:/absolute/path/shot.png
```

```text
command=save_state
path=C:/absolute/path/gameplay.state
```

```text
command=load_state
path=C:/absolute/path/gameplay.state
```

```text
command=stop
```

Other commands: `pad`, `clear_pad`, `pause`, `resume`, `read_memory`,
`write_memory` (see `automation_protocol.cpp` for exact fields).

`status.txt` fields are useful for evidence:

```text
state=running
booted=1
fps=59.94
vps=59.94
speed=1.0
frame_count=...
present_count=...
title=...
game_id=...
game_name=...
navigation_...
last_command=...
last_error=
```

For deterministic benchmarks, pass `--load-state <file>` and then only read
`status.txt`; do not rely on navigating menus for every run.

## Dispatch samples

```powershell
$env:STATICRECOMP_DISPATCH_SAMPLES="1"
runner ... --automation-dir <auto>
# wait 20-30 s
"command=stop" | Set-Content <auto>\commands\stop.txt
```

At shutdown the log prints the top 16 guest PCs. Map them:

```powershell
python tools/dol_disasm.py work\disc\main.dol 0x8011EF00 0x8011EF90
```

Use the generated chunk file to find the function/loop containing the PC.
Dispatch samples are frequency, not time; combine with PGO counts and the
CPU/GPU split.

## Common boot failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `no native module was supplied; use allow_interpreter explicitly` | JIT mode without permission | pass `--allow-interpreter` or set it in the runner for `--core jit` |
| `module loaded` missing | wrong path/name, `--module` not passed | check `g<ID>_recomp.dll`, exe dir, user `StaticRecompModules` |
| `unsupported disc ID` | wrong region/revision | use the exact supported dump |
| `unsupported main DOL` | bad rip or patched DOL | verify SHA-256/Redump |
| `invalid config.ini line` | unknown key is not the issue; a malformed line is | check the line number/value; parser skips sections |
| black legal/title | EFB access off | set `efb_access=true` |
| `SMC hash mismatch` repeatedly | cache-op/emitter or SMC range bug | fix cache emission/SMC tracking; do not disable verification |
| crash on exit from fullscreen | window callback after config teardown | fix platform shutdown/fullscreen ordering |
| controller missing | no GCPadNew.ini | auto-detect first SDL gamepad or generate the profile |
| RecompLauncher sees no ISO | `kind: iso` and RVZ picked | convert to ISO |
| RecompLauncher stale releases | 6-hour release cache | Settings -> Check Now / restart |

## Test matrix

Minimum before shipping:

- [ ] legal screen, title screen, intro/logo movies
- [ ] gameplay from a real save state in at least two areas
- [ ] pause menu, Options, Save, Load
- [ ] memory-card save/load
- [ ] fullscreen and windowed
- [ ] controller (real pad)
- [ ] one graphics settings change, confirm `[video]` log
- [ ] RecompLauncher setup from ISO, verified badge, settings, Play
- [ ] update from previous release (if applicable)
- [ ] clean install in a new folder
- [ ] release asset download-back check

## RecompLauncher-specific tests

1. Install/update the entry; confirm checksum matched.
2. Open the game page: manifest read, Easy Setup badge, Settings tab, CPU core.
3. Setup: pick ISO, confirm disc ID/CRC badge, progress lines, `Game/` created.
4. Change a setting; inspect `config.ini` and the next `[video]` log.
5. Press Play: runner starts directly, fullscreen, controller works.
6. Verify saves/logs folders and that an update preserved `Game/`.
7. Confirm no game data in the release zip.

## Evidence to keep

- `status.txt` snapshots
- log tail
- screenshots of setup/settings/title/gameplay
- exact config and command line
- before/after benchmark table
- release hash/schema/content scan

## When stuck

1. Restate the last known-good state and the first failing change.
2. Reproduce with a save state, not by replaying menus.
3. Compare static vs JIT, low vs high, vsync on/off.
4. Read the actual log line; do not infer from FPS alone.
5. Try one variable at a time; keep a ledger.
6. After three failed variations, change approach or ask for the missing disc
   region/state/log.
