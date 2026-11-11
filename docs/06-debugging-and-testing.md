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

`[staticrecomp] SMC: chunk ... accepted data-only write` is healthy. A
`hash mismatch; interpreter until next invalidation` line means code changed
and the runtime correctly fell back; repeated mismatches point at a
cache-op/SMC bug.

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

### Automation input rules

These were learned the hard way and apply across projects:

- **Automation is the only reliable input path.** Synthetic
  `keybd_event`/`SendKeys` did not reach the game even with a keyboard
  `GCPadNew.ini`, in a non-interactive session. Use `command=pad_frames`.
- **The first pad command after `--load-state` is swallowed.** Send it twice,
  or wait a frame and send it again.
- **Short taps beat long holds.** Three-frame A taps every ~3 s advanced
  menus, character select and arena select. Long holds were ignored on some
  screens.
- **Never send the all-buttons combo.** It includes B; a game can interpret it
  as "back" and drop into the attract demo.
- **Screenshots come from the guest framebuffer.** They are unaffected by other
  windows and can be compared frame to frame.
- **Read `fps` after warm-up.** During boot/streaming it reads 2-3 while assets
  load; `vps` and `speed` stay near 1.0.

### State ladder

Build a ladder of save states as soon as the game reaches each screen:

```text
title.sav -> mainmenu.sav -> select.sav -> in-game.sav
```

Then: regression tests load the earliest state that should still work, and
benchmarks load the deepest. A state ladder is also how you prove a control
change did not break the menus without replaying them.

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

## Verifying a false SMC failure

A chunk hash mismatch is not automatically a code patch. The engine may use
zero-filled space inside `text` for runtime tables.

1. Dump the retired chunk with the automation channel:

   ```text
   command=read_memory
   address=0x801E72C0
   size=16384
   path=C:/work/chunk.bin
   ```

2. Diff it against the retail DOL's bytes for the same virtual range.
3. If **every changed byte was `0x00` in the retail image**, it is a data
   write. SpongeBob's mask table contained the string `DEFAULT` and pointers;
   no instruction byte changed.
4. If any changed byte was nonzero in the retail image, treat it as a real
   self-modifying-code event and find the writer.

The runtime fix (SpongeBob) keeps a copy of the retail DOL, accepts
changes that only touch originally-zero bytes, updates the effective hash and
keeps the chunk native; anything else still falls back to the interpreter.
Result: `accepted data-only write`, `smc_failed=0`, no interpreter retirement.

Do not silence SMC verification to make the log look clean.

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
| crash/hang on exit from fullscreen | runtime fullscreen teardown, or swap-chain image cleared while still marked valid | windowed creation + delayed fullscreen; validate index/texture/framebuffer; log/skip failed recreation; see [04](04-runtime-and-launcher.md#fullscreen-and-shutdown-windows) and [09](09-troubleshooting.md#window--shutdown) |
| `0xC0000409` during `inspect` or first boot | `std::filesystem::generic_string()` threw on a non-ANSI (Shift-JIS) file name; `terminate` -> `__fastfail` | sort with `lexically_relative()`, name with `generic_u8string()`; see below |
| settings saved but ignored; no `[video]` line | runner binary predates the option | rebuild the runner from the current runtime; pass `--core static` for a generic runner |
| `Failed to initialize DSP emulation!` | `Sys/GC/dsp_rom.bin` / `dsp_coef.bin` missing next to the runner | ship both files with the release |
| controller missing | no GCPadNew.ini | auto-detect first SDL gamepad or generate the profile |
| controller profile loads but no input | wrong device string (`Source/Id/Name`), or D-pad is not movement | verify at the guest pad register, not the file; remap per game |
| RecompLauncher sees no ISO | `kind: iso` and RVZ picked | convert to ISO |
| RecompLauncher stale releases | 6-hour release cache | Settings -> Check Now / restart |

### Non-ASCII paths

`0xC0000409` is `STATUS_STACK_BUFFER_OVERRUN`, which is also what
`__fastfail` reports. Before assuming a stack overflow, check the extracted
tree for names that are not representable in the ANSI codepage.

```powershell
Get-ChildItem work\game\files -Recurse -File |
  Where-Object { $_.Name -match '[^\x20-\x7E]' } |
  Select-Object -First 20 FullName
```

Two developer-leftover PSDs with Shift-JIS names are enough to kill
`moderngekko-port inspect` and the runner. Quarantine them to confirm, then fix
the hash walk (`lexically_relative` + `generic_u8string`) rather than renaming
retail files.

## Fullscreen shutdown regression

Symptom: fullscreen ALT+F4 hangs or exits with `0xC0000005`.

1. Check Event Viewer / WER for the faulting module, exception code and offset.
2. Open the minidump; `ExceptionInformation [1, 0x40]` means a write to
   `null + 0x40`. Map the fault RVA and look for `VKGfx::BindBackbuffer`.
3. Read the thread names: the crashing thread is usually `CPU-GPU thread`
   (single-core) or the CPU thread. A stack through `Presenter::Present` and
   `VKGfx::BindBackbuffer` points at the present path.
4. For a hang, capture a mini dump with
   `procdump64 -accepteula -mm <pid> <dump>`; a full `-ma` dump can be tens of
   GB. Enumerate the process windows: a hidden `#32770` "Warning" dialog is a
   blocking `PanicAlertFmt`, not a normal close.
5. Inspect `SwapChain::IsCurrentImageValid()`, `DestroySwapChainImages()`,
   `AcquireNextImage()` and whether `BindBackbuffer()` checks the current
   texture/framebuffer.

Fix: create the window windowed, apply fullscreen after video initialization,
do not toggle fullscreen in the platform destructor, validate the current
image, log/skip a failed recreation, and add a short shutdown grace period.
Also skip the presenter's frame-pacing sleep when the core is stopping, and
add a last-resort shutdown watchdog for remaining Vulkan/shader waits.

## Test matrix

Minimum before shipping:

- [ ] legal screen, title screen, intro/logo movies
- [ ] gameplay from a real save state in at least two areas
- [ ] pause menu, Options, Save, Load
- [ ] memory-card save/load
- [ ] fullscreen and windowed
- [ ] ALT+F4 from fullscreen (one press) -> clean exit, no crash dump
- [ ] F11 leave/re-enter fullscreen, then close
- [ ] close after loading a gameplay save
- [ ] fullscreen double-close
- [ ] no hidden `#32770` "Warning" dialog or modal panic
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
5. Press Play: runner starts directly, fullscreen, controller works; ALT+F4
   exits cleanly and writes no crash dump.
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
