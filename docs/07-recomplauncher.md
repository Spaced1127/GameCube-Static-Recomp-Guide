# 07 - RecompLauncher

RecompLauncher installs and updates a recomp from GitHub releases. The recomp
itself does not change; the launcher reads one `recomplauncher.json` and does
what a player would do by hand.

Official material:

- Guide: <https://recomplauncher.com/sdk-files/guide.md>
- Schema: <https://recomplauncher.com/schema/recomplauncher.json>
- FIFA example: <https://recomplauncher.com/sdk-files/examples/fifawc14.json>
- Streetball example: <https://recomplauncher.com/sdk-files/examples/streetball.json>

A copy of the schema (source: <https://recomplauncher.com/schema/recomplauncher.json>)
is included at [docs/recomplauncher.schema.json](recomplauncher.schema.json).
Validate every manifest before shipping:

```powershell
python tools/validate_manifest.py docs\recomplauncher.schema.json `
  path\to\recomplauncher.json
```

## Levels

| Level | Player gets | Manifest fields |
|---|---|---|
| 1 | Drop in a disc, setup, Play starts the game | `game`, `start` |
| 2 | Settings on the game page / Big Picture | `config`, `settings` |
| 3 | Custom prepare step + verified dump badge | `prepare`, `game.dumps` |

## Release requirements

- One file per system, with the system and processor in the name:
  `MyRecomp-v1.2.0-Windows-x64.zip`, `MyRecomp-v1.2.0-Linux-x64.AppImage`.
- A `.zip`/`.7z` folder on Windows. An installer `.exe` is a last choice.
- `recomplauncher.json` at the **top** of the zip, next to the executable.
- No game data.
- Keep `symbols`, `source`, `pdb`, `.sha256`, `.sig`, `.asc` files out of the
  asset selection path.
- Updates unpack over the game folder; saves/settings/caches survive. A
  settings file inside the release would overwrite the player's, so ship
  defaults via `config.new` or a separate `default.*`.

## `game`

```json
"game": {
  "kind": "iso",
  "label": "Your USA GameCube disc image (.iso) of ... (GSQE78).",
  "dumps": [
    { "name": "USA", "size": 1459978240, "crc32": "f2facf74" }
  ]
}
```

- `kind`: `iso`, `folder`, or `iso_or_folder`.
- `label`: what to ask for; name the region/serial if only one works.
- `check`: `file`, `xdvdfs`, or `iso9660` only.

### GameCube limitation

GameCube discs are **not ISO 9660**. The SDK has no GameCube check. Do not put
an `iso9660` check on a GameCube manifest. For a plain ISO:

- omit `check`
- include `game.dumps` (Redump size/CRC-32)
- let `prepare` validate the disc ID and retail DOL
- the player picks the ISO manually

For ISO or extracted folder, Rocket Power's approach:

```json
"kind": "iso_or_folder",
"check": { "ids": ["GBQE78"], "file": "sys/main.dol" }
```

The SpongeBob example uses `kind: "iso"`, no `check`, and Redump dumps; see
[examples/spongebob/recomplauncher.json](../examples/spongebob/recomplauncher.json).

RVZ: the custom launcher may support it, but RecompLauncher's `iso` kind may
reject a compressed RVZ. Either convert to ISO or document the limitation.
The SpongeBob manifest advertises ISO only.

## `prepare`

```json
"prepare": {
  "program": ["SpongeBobRecomp.exe"],
  "args": ["--extract", "{game}"],
  "label": "Extracting the game files from your disc",
  "timeout": 1200
}
```

- Runs headless; no window.
- Print `progress <0-1> <text>` lines.
- Exit 0 on success; non-zero is a failed setup with the exit code.
- Write to the same place the custom launcher would, so both stay in step.
- Runs after the copy is checked, before settings are written.
- Runs again if the player changes their copy.

SpongeBob's extractor prints `progress 0.000 Opening ...` through
`progress 1.000 Extraction complete`.

## `start`

```json
"start": {
  "program": ["SpongeBobRecompRunner.exe"],
  "args": [
    "--module", "{install}/gGSQE78_recomp.dll",
    "--user-dir", "{local}/SpongeBobRecomp"
  ]
}
```

- `program` paths are tried in order; the first existing one runs.
- `args` are always passed; player launch options are appended.
- `env` sets environment variables (letters/digits/underscore; system vars
  like `PATH` cannot be set).

Useful RecompLauncher variables available to the game:

```text
RECOMPLAUNCHER=1
RECOMPLAUNCHER_VERSION=...
RECOMPLAUNCHER_MODE=bigpicture|desktop
RECOMPLAUNCHER_PAD=xbox|playstation
```

### JIT/static core via env

Rocket Power's manifest starts with:

```json
"env": { "MODERNGEKKO_STATICRECOMP": "0" }
```

SpongeBob exposes it as a setting instead:

```json
{
  "id": "core",
  "label": "CPU core",
  "in": "args",
  "help": "JIT runs at the full 60 FPS. Static recomp is the faithful static build but can dip in heavy scenes.",
  "choices": [
    { "label": "JIT (60 FPS)", "args": [] },
    { "label": "Static recomp", "args": ["--core", "static"] }
  ]
}
```

The runner defaults to JIT when `cpu_core=jit`; the static choice appends
`--core static`. If you use `env`, remember it applies to every start; a
per-launch `--core` argument is more flexible.

## `config`

```json
"config": [{
  "id": "main",
  "format": "ini",
  "file": [{ "path": "{local}/SpongeBobRecomp/config.ini" }],
  "ensure": { "efb_access": "true" },
  "always": { "efb_access": "true", "emulation_speed": "1" },
  "new": {
    "resolution": "1920x1080",
    "backend": "Vulkan",
    "fullscreen": "true",
    "msaa": "2",
    "ssaa": "false",
    "efb_access": "true",
    "emulation_speed": "1",
    "cpu_core": "jit"
  }
}]
```

- `format`: `toml`, `ini`, or `json`; edited line by line for INI/TOML.
- `file`: first existing path with a true `if`, otherwise the fallback.
- `game_path`: key that receives the player's copy path on every start.
- `ensure`: set only when missing/empty.
- `always`: set on every start (keep minimal).
- `new`: defaults only when the file does not exist.
- Values are written exactly; TOML strings keep quotes.
- INI section-qualified keys are supported (`Video/resolution`). The game's
  parser ignores sections, so flat keys work too.

## `settings`

```json
{
  "id": "resolution",
  "label": "Resolution",
  "help": "The internal render resolution, not the window size.",
  "choices": [
    { "label": "3x (1920x1080)", "set": { "resolution": "1920x1080" } }
  ],
  "defaults": { "resolution": "1920x1080" }
}
```

- File settings: each choice's `set` writes keys into the `in` config (default
  `main`). The first choice whose keys all match the file is shown. Missing
  keys are read from `defaults`.
- Command-line settings: `"in": "args"` and each choice has `args`. An empty
  `args` is a good default ("Game's option" or "JIT").
- `when` greys out a setting unless keys match.

Keep labels short and help to one sentence. Expose what players care about:
resolution, frame rate, AA, VSync, window mode, core. Do not expose an
uncapped/150%/200% frame rate if the game is capped.

## `saves`, `folders`, `actions`, `exit_codes`

```json
"saves": ["{local}/SpongeBobRecomp/GC", "{local}/SpongeBobRecomp/StateSaves"],
"folders": {
  "saves": [{ "path": "{local}/SpongeBobRecomp/GC" }],
  "logs": [{ "path": "{local}/SpongeBobRecomp/Logs" }]
},
"actions": [
  { "id": "saves", "label": "Saves", "open": "saves" },
  { "id": "logs", "label": "Logs", "open": "logs" }
],
"exit_codes": {
  "2": "The game couldn't start. Check the Logs folder."
}
```

- `saves`: folders/files/globs; copied after each session (newest ten stay
  locally); nothing over 64 MB.
- `folders`: named places the launcher can open/clear.
- `actions`: buttons under settings; `open`/`clear`.
- `exit_codes`: friendly messages for known codes.

## Assets and platform detection

- Name assets `Name-vX.Y.Z-Windows-x64.zip` / `-Linux-x64.AppImage`.
- The launcher picks the file by OS/arch words. "Windows" and "x64" work.
- A zip with one top folder is unwrapped.
- Do not use `debug`, `symbols`, `pdb`, `source` in asset names.
- GitHub's SHA-256 digest is checked on download; no extra checksum needed.

## Release cache and updates

- The launcher caches a repo's release list for **6 hours**.
- Settings -> Updates and Downloads -> **Check Now** forces a refresh (once a
  minute).
- Replacing a release asset without changing the tag does **not** create an
  update for existing installs. Bump the version for real updates.
- Pre-releases are betas; normal players stay on the latest full release.

## Test the actual UI

1. Install/update the entry; confirm checksum matched.
2. Open the game page: Easy Setup badge, Settings tab, CPU core, no red
   manifest errors.
3. Setup: choose the ISO; confirm "Matches the verified USA disc" (Redump
   size/CRC), progress lines, `Game/` and `default-game.txt`.
4. Change a setting; inspect `config.ini`; press Play; confirm the next
   `[video]` log.
5. Verify Play starts the runner directly (not the custom launcher), fullscreen,
   controller, saves/logs.
6. Update from the previous release and confirm `Game/` survived.
7. Download the release asset back and confirm hash/contents/no game data.

## Common RecompLauncher pitfalls

- `check` missing for GameCube -> player must pick the ISO; that is expected.
- RVZ rejected by `kind: iso` -> convert to ISO.
- Manifest at the top level only; a nested copy is ignored.
- A stale release cache -> Check Now.
- A same-tag asset replacement -> no update; use a new version.
- Settings write to the wrong file/section -> verify with the next run's log.
- A `prepare` that opens a window or prints no progress -> bad setup UX.
- Game data in the zip -> never.
