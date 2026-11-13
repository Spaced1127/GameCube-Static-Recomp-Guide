# 15 - Launcher parity and per-title theme

The launcher is the player's front door and the part of a port most likely to
drift between titles. This chapter is the contract: **every port ships a
launcher built from the shared shell, with the same feature set. Only the theme
changes per title.** Parity means the same capabilities in the same places, not
identical pixels.

A feature added for one title goes into the shell, so every later launcher
build gets it. A title fork is a bug, not a shortcut.

For the concrete build recipe (shell anatomy, theme tokens, and the gotchas
that block agents), see [16 - Launcher implementation](16-launcher-implementation.md).

## The structural contract (two executables)

Parity starts with the *structure*, not the pixels. Every port ships exactly
two player-facing executables: the launcher (`<Title>Recomp.exe`) and a single
runner (`<Title>RecompRunner.exe`). The flow is **launcher -> Play -> runner**.

- The runner selects the CPU core itself (`--core jit|static`). There is **no
  runner shim and no separate "core" executable**.
- There is **no `Play.cmd`** (or any batch shim); the launcher is the entry point.
- RecompLauncher's `prepare` runs the launcher headless (`--extract`); there is
  **no separate shipped `Prepare.exe`**.
- The custom launcher and `recomplauncher.json` share one user dir, module name
  and config path.

A port that ships a shim/core pair, a `.cmd`, or a separate prepare exe is not
at parity even if it looks finished. The full rationale and CMake wiring are in
[16](16-launcher-implementation.md#1-the-two-executable-architecture-get-this-right-first).

## The launcher parity contract

Every launcher, regardless of title, must provide:

| Area | Capability |
|---|---|
| Setup | import the disc, verify ID/DOL/Redump data, extract with progress, expose headless `--extract` for RecompLauncher |
| Settings | resolution/scale, MSAA/SSAA/AF, VSync, fullscreen/window, audio backend and volume, core (JIT/static), widescreen where supported |
| Input | detect a pad, write a valid profile (`Source/Id/Name`), show the mapping, apply the title's default |
| States | list, save, load, delete, and reveal the state folder |
| Cards | create the folder card, back up, import `.gci`, reveal the path |
| Host checks | create `Cache\Shaders`, set physical-core affinity and `High` priority, verify the DSP ROMs, and document the per-app mute check |
| Diagnostics | open logs, copy the log tail, show module and runner provenance (`[video]` line) |
| Close | wait for the process, kill the tree after a timeout, never show a modal on close |
| Updates | about/version, update check, and a release-cache refresh path |
| Theme | apply the theme (names, icons, strings); never require code changes for art or strings |

Two of these are not optional because they were measured bugs elsewhere: the
shader cache directory and the shutdown guard. A title without them is not at
parity, even if it looks finished.

## Per-title theme

The theme is data and art, not logic:

- product and executable names;
- launcher badge and runner cover icons;
- accent colour, splash and about text;
- window title and player-facing strings;
- manifest `label`, `settings.help` and `exit_codes`;
- `PLAYERS.md`, README and release notes.

Controller defaults and save/card names are title data, but they are still
configuration, not a launcher fork.

## Rules

1. Build every launcher from the current shell. Do not ship an older binary
   because the theme still works.
2. A title may not silently omit a parity feature. Record an exception in
   `STATE.md` with the reason and the owner.
3. Theme is data. If a theme needs code, it is a shell feature.
4. The custom launcher and `recomplauncher.json` use the same user dir, module
   path and config path. Two paths means two support cases.
5. A generic runner has no disc gate; a per-title runner is never reused for
   another title.
6. The theme audit is part of release: no other title's name, icon or disc ID
   in the binaries, manifest, README or logs.

## How to audit parity

On a fresh user dir, with no save state:

1. Build the launcher from the current shell.
2. Walk the parity table above; every row must pass or be a recorded exception.
3. Start once from the custom launcher and once through RecompLauncher; both
   must use the same user dir and write the same config.
4. Change one setting in each surface; confirm the next `[video]` line shows it.
5. Close from fullscreen and from windowed; one clean exit, no dump.
6. Take a screenshot of each settings page and compare two ports side by side:
   same tabs, same order, same paths, different theme.

Record it in `STATE.md` as
`Launcher: shell <revision>, theme <title>, parity <date>`.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| a setting exists on one port and not another | launcher forked per title | port the feature into the shell, rebuild every launcher |
| a release opens the wrong game or rejects the disc | per-title runner shipped as a generic one | rebuild without the disc gate, or ship one runner per title |
| an update loses saves or settings | manifest and launcher disagree on the user dir | one path, used by both surfaces |
| another title's art or strings appear | theme copied wholesale | replace name/icons/manifest strings; run the theme audit |
| a fixed bug returns after a release | launcher built from an old shell | rebuild from the current shell, not from the last asset |
| RecompLauncher works but the direct launcher does not | different config or module paths | align both to the same user dir and module name |

## Acceptance

- [ ] Launcher built from the current shell; parity table passed on a fresh
      user dir.
- [ ] Theme audit passed; no other title's branding or disc ID.
- [ ] Manifest schema 0 errors; manifest and launcher paths agree.
- [ ] Both surfaces expose the same settings and write the same config.
- [ ] Fullscreen and windowed close are clean, with no dump.
