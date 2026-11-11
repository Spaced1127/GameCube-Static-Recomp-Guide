# 13 - Other targets and the honest port

This guide ships a Windows build because that is where the pipeline was
validated. The same project often needs a second target: a handheld, a console,
a Steam Deck, or a "portable" build for a device that already runs a
Dolphin-derived emulator. Decide which of the three paths you are on before
writing code, because they have different acceptance criteria.

## Path A - run the retail game on a Dolphin-derived runtime

This is the cheapest way to get the actual game onto a handheld, and it is not
a static recompilation. It reuses the game's own PowerPC code through a JIT
core and a platform renderer. Call it what it is in the README: running the
retail game on an emulator port. Do not label it "native port" or "recomp".

What was verified with Nezumiiruka v1.1.0 (a Dolphin fork with a deko3d
renderer) and Rocket Power: Beach Bandits on Switch:

| Item | Result |
|---|---|
| Layout | `sdmc:/switch/nezumiiruka/{nezumiiruka.nro,roms/<disc>.iso}` |
| Renderer | **deko3d** build; Vulkan build kept only for A/B |
| Internal resolution | 1x (640x480), no AA, no AF, no widescreen hack |
| Disc format | RVZ is smaller and the author's recommendation; ISO is a fallback |
| Keys/firmware | not needed for GameCube |
| Performance overlay | L3 + R3 |

### The setting that fakes a CPU bottleneck

The most expensive mistake was a non-100% emulation speed limit. A 90% speed
limit looks exactly like "CPU-bound at 88-95%": audio warbles, the overlay
shows ~90% speed, and no amount of overclocking fixes it.

Check, in this order:

1. **Speed limit / Emulation Speed = 100%.** Leave "Disable Emulation Speed
   Limit" off; the target is 100%, not uncapped.
2. **CPU clock override** (Dolphin's Emulated CPU Clock Override) at 100%
   first. If FMV-heavy scenes are still short, 85-95% can raise host speed;
   85% brought this game's FMVs to ~99-100%. Lower values can break game
   timing, so keep the highest value that holds speed and does not change
   physics or audio.
3. **Per-game override.** `GameSettings/<ID>.ini` silently overrides
   `Config/Dolphin.ini`; delete or match it.
4. **Horizon OC actually applied.** "Maxed out" in the overlay proves nothing.
   Run the OC monitor while the game is running and confirm clocks,
   temperatures and "Kip is not loaded!".
5. Then, and only then, tune audio and graphics.

The tested config for this title:

```ini
[Core]
EmulationSpeed = 1.000000
Overclock = 0.850000
OverclockEnable = True
```

Audio and graphics settings that held up: DSP HLE, preserve pitch on speed
changes, 40-80 ms latency; dual core on; skip idle on; EFB/XFB copies to
texture (turn off if FMVs go magenta or menus break); ubershaders or
specialized shaders to avoid compile stutter.

### RVZ vs ISO on a handheld

The CPU pays for decompression while the game runs. In this project RVZ was
fine for gameplay and menus, and the earlier ISO recommendation was not the
FMV fix. Prefer RVZ for card space and A/B the ISO only if a specific title's
FMVs stutter. Any claim that the container fixed speed needs the speed-limit
check first.

## Path B - cross-compile the static recomp

The static module is host C. Cross-compiling it is ordinary compiler work; the
runtime is the hard part, because it carries the GX/VI/DSP/input backends.
Before promising this path:

- confirm the runtime builds for the target toolchain (a GNU-style Clang build
  of the vendored Dolphin tree failed in `Externals/libusb` with a `timespec`
  redefinition against the Windows SDK UCRT in one project; the same class of
  failure exists on other targets);
- confirm the target has a GPU backend the runtime supports (Vulkan, GLES,
  deko3d, ...);
- confirm input, audio and memory-card paths exist;
- keep the module's `x86-64-v3` build separate from a target build. Do not
  reuse a desktop module.

No part of this guide has a measured static-recomp build on a console. Treat
it as unproven until a real run exists, and say so.

## Path C - a from-scratch viewer or partial port

A useful intermediate step: portable readers for the archive, textures and
meshes, plus a small renderer. It proves the formats and produces inspectable
output without claiming to be the game.

What this proved in Rocket Power on Switch (a 276 KB homebrew `.nro`):

- the retail archive is readable from the SD card at runtime;
- TPL/CMPR decodes correctly (bit-identical against Pillow);
- `OB11` meshes and `.ent`/`.dbx` level composition are correct;
- a CPU software renderer draws the Lakes Hub (45 instances, 33k verts) and
  WaveBike (120 instances, 37k verts) with textures;
- a deko3d path can upload the same flattened mesh and draw it with a depth
  buffer.

What it did not do: run the game's logic, audio, menus or collisions. Be
precise about this in release notes; "asset viewer" and "port" are different
claims.

## Handheld rules that carry over

- **Do not expose uncapped speed.** 100% is the target. A "faster" mode that
  desyncs audio is not a feature.
- **Warm the pipeline cache.** First-run shader compilation looks like a CPU
  stall on any platform.
- **Verify the clock, not the slider.** An overclock profile that is not
  loaded, or is applied to the wrong title ID, is the same as no overclock.
- **Keep the desktop build as the reference.** When a device is short, compare
  the same save state on desktop before changing settings.
- **Never ship game data.** The SD card gets the player's own disc, extracted
  at runtime or copied by the player. A release zip contains code only.

## devkitPro toolchain notes (WSL/Linux)

These cost a session each and are worth keeping:

- **The makefile chain is not path-safe.** A project under a path with spaces
  (`H:\Projects\RPBB Gamecube Decomp`) fails with
  `/mnt/h/Projects/RPBB: No such file or directory`. Stage the sources into a
  short `/tmp` path, build there, copy the `.nro` back.
- **`/tmp` may not survive between `wsl.exe` invocations.** Build host tools
  into `work/build/` instead.
- **`pacman-key` is broken on some Ubuntu images.** `pacman-package-manager`
  sources `makepkg` helpers the distro package does not ship; use
  `SigLevel = Never` plus the signed database over HTTPS.
- **Cloudflare fronts the devkitPro repos.** Plain `curl` gets a 403
  "Attention Required"; a browser User-Agent is accepted, so point
  `XferCommand` at `curl` with one.
- **Do not put the toolchain, the archive or the built `.nro` in Git.**

## Acceptance for a non-Windows target

- [ ] The README says which path this is (emulator port, static recomp, or
      viewer) without marketing language.
- [ ] Speed limit is 100%; no uncapped option shipped.
- [ ] Same save state compared against the desktop build.
- [ ] Clock/thermal state verified during the test, not assumed.
- [ ] The player supplies their own disc; no game data in the release.
- [ ] Every performance claim has the overlay numbers and the settings used.
