# AGENTS.md

Instructions for AI agents working on a GameCube static recomp **using this
guide**. These are rules for the agent, not game content. Read the project's
own `AGENTS.md`/`STATE.md` first if one exists.

## Read order

1. `README.md`
2. `docs/00-quickstart.md`
3. `docs/01-architecture.md`
4. `docs/05-performance.md` if the task is performance
5. `docs/07-recomplauncher.md` / `docs/08-icons-and-release.md` if the task is
   packaging
6. `docs/12-asset-formats.md` if the task touches archives/textures/levels, or
   `docs/13-other-targets.md` for a non-Windows target
7. `docs/15-launcher-parity.md` (the contract) and
   `docs/16-launcher-implementation.md` (the build recipe + gotchas) if adding a
   launcher feature, building/theming a launcher, or shipping a release
8. The target project's `STATE.md`, build scripts and latest logs

## Hard rules

- **No game data** in Git, releases, test fixtures or generated docs: no
  ISO/RVZ/WBFS/GCM, DOL, FST, `Game/`, textures, audio, saves or cover art.
- **No generated-code edits.** Fix the emitter/runtime and regenerate.
- **Launcher parity, per-title theme.** Every port ships the shared launcher
  feature set; only names, icons, strings and manifest labels change. Add a
  feature to the shell, never to one title's fork. Ship exactly two executables
  (launcher + single runner with native `--core`); no shim, no `RunnerCore`, no
  `Play.cmd`, no shipped `Prepare.exe`. See
  [docs/15](docs/15-launcher-parity.md#the-launcher-parity-contract) and
  [docs/16](docs/16-launcher-implementation.md).
- **No clean builds** unless the user explicitly asks. DolRecomp/Dolphin
  builds and PGO data are expensive.
- **No commit, tag, release or push** without explicit user approval. A request
  to "fix" is not permission to publish.
- **No claim without evidence.** Build, run, load a real state, read
  `status.txt`, inspect the log. "Should work" is not evidence.
- **Ask for the missing input** (disc ID/DOL hash, save state, log, exact
  reproduction) instead of guessing.
- **Stop after three failed variations** of the same fix. Name the assumption,
  test it directly, and change approach.

## Build gate

Before saying a change is done:

```powershell
# inspect the extracted tree (disc ID, entry, DOL hash)
moderngekko-port inspect <Game>

# compile
cmake --build build\moderngekko --target moderngekko-run moderngekko-launcher -j 8

# run a deterministic state
runner --game <Game> --module <module.dll> --user-dir <test-user> `
  --load-state <state.sav> --graphics Vulkan --audio Null `
  --automation-dir <auto> --allow-interpreter

# read
Get-Content <auto>\status.txt
Get-Content <test-user>\Logs\ModernGekko.log -Tail 60
```

For a release, also download the uploaded asset back and verify the SHA-256,
manifest schema, top-level contents, icons, and absence of game data.

## Performance rule

Never assume a dip is GPU or CPU:

0. **Fix the host first.** Pin to physical cores (`0xFF` on 16 threads), create
   `<user-dir>\Cache\Shaders`, warm the pipeline cache, confirm the app is not
   muted, and close background GPU/CPU load. Two of these were worth ~20% and
   removed false "codegen" symptoms.
1. Run the same state at **1x, no MSAA/SSAA** and at the shipped settings.
2. If low settings are not significantly faster, it is CPU-bound.
3. Run the **JIT reference** (`MODERNGEKKO_STATICRECOMP=0` or `--core jit`).
4. If JIT holds the target and static does not, use JIT as the playable path
   and keep the static module as an optional artifact. Do not spend days
   micro-optimizing a 40% static gap.
5. If static is close, profile with PGO counts and
   `STATICRECOMP_DISPATCH_SAMPLES=1` before changing code.
6. If a release ignores a setting, check that the runner binary was rebuilt
   from the current runtime (the `[video]` line proves it).

The GameCube VI is **59.94 Hz**. A title showing 59.9 is full speed.

## Evidence to keep

- `status.txt` with `fps`, `vps`, `speed`, `frame_count`, `present_count`
- log tail with `[video]`, `[audio]`, `[staticrecomp]` stats
- exact command line and config file
- before/after numbers
- for release: asset hash, schema result, content scan, icon extraction

## Project state

Create/maintain a `STATE.md` in the target project:

```markdown
# STATE
- Disc: <ID>, DOL SHA-256, Redump size/CRC
- Build: module path, compiler flags, PGO profile
- Runtime: static/JIT, config, known-good save state
- Performance: baseline, current, target
- Open issues: symptom -> first PC/log line -> owner
- Release: tag, asset, hash, RecompLauncher status
```

## Definition of done

- It builds from the documented command.
- It boots and reaches gameplay from a real save state.
- The measured target is met (or the limitation is stated with evidence).
- Logs show no new fallbacks/SMC failures/crashes.
- RecompLauncher manifest validates and the release contains no game data.
- The launcher passes the parity table in `docs/15` on a fresh user dir, and
  the theme audit shows no other title's branding or disc ID.
- The user has approved any public action.
