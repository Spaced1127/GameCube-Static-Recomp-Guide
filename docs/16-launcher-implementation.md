# 16 - Launcher implementation: build the shell, then theme it

This is the concrete companion to [15 - Launcher parity](15-launcher-parity.md).
Chapter 15 is the *contract* (what every launcher must do). This chapter is the
*recipe* (how to build it so it actually works), distilled from the SpongeBob
(`GSQE78`) and WWE Day of Reckoning 2 (`GW2E78`) ports, where the same bugs cost
hours each. If you are an agent asked to "make the launcher like the other
ports but themed for my game", read this whole page before writing code.

The canonical shell is `tools/moderngekko_launcher.cpp` in the ModernGekko
submodule, as adapted in the SpongeBob and DOR2 ports. **Copy that shell; do not
rewrite it from scratch.** Theming is data and art, never a fork of the logic.

---

## 1. The two-executable architecture (get this right first)

Most launcher pain comes from shipping the wrong *structure*, not the wrong
pixels. The shared launcher ships exactly **two player-facing executables**:

```
<Title>Recomp.exe          the launcher: import disc, settings, Play
<Title>RecompRunner.exe    the runner: the actual ModernGekko runtime
g<ID>_recomp.dll           the static module (code only, no assets)
Sys/                       shaders, runtime tables, DSP firmware
LICENSES/                  Dolphin, DolRecomp and project licenses
dor2_grid.png / _logo.png  per-title launcher art (optional, falls back)
README.txt / PLAYERS.md
recomplauncher.json        RecompLauncher manifest, at the TOP of the zip
```

The flow is **launcher -> Play -> runner**. The player opens one file
(`<Title>Recomp.exe`), changes settings, clicks Play, and the game starts.

### Anti-patterns that break parity (do not ship these)

| Anti-pattern | Why it is wrong |
|---|---|
| A `Play.cmd` / `.bat` shim that just starts the launcher | Redundant third entry point; the launcher already starts the runner. Delete it. |
| A runner *shim* exe plus a separate `...RunnerCore.exe` | Two divergent launch paths and a stderr-tee crutch. The runner selects the core itself. |
| A separate `...Prepare.exe` in the release for RecompLauncher | The launcher already extracts headless via `--extract`. Use it. |
| Per-title forks of the launcher logic | A feature added for one title must go into the shell so every port gets it. |

### The runner selects the CPU core natively

The upstream ModernGekko runner picks its core from the `MODERNGEKKO_STATICRECOMP`
environment variable and has **no `--core` switch**. Add one to
`tools/moderngekko_run.cpp` (this is the single most important parity edit):

```cpp
// argument loop
else if (arg == "--core") {
  const std::string selected = value("--core");
  if (selected != "jit" && selected != "static") {
    std::cerr << "--core must be jit or static\n";
    return 2;
  }
  core_mode = selected;
}

// after config.ini is parsed
if (core_mode.empty())
  core_mode = frontend_config.cpu_core;          // config.ini fallback
#if defined(_WIN32)
  _putenv_s("MODERNGEKKO_STATICRECOMP", core_mode == "static" ? "1" : "0");
#else
  setenv("MODERNGEKKO_STATICRECOMP", core_mode == "static" ? "1" : "0", 1);
#endif
if (core_mode != "static")
  config.allow_interpreter = true;               // JIT needs interpreter permission

// module discovery: JIT deliberately ignores the static module
if (core_mode != "jit" && module_path.empty()) { /* ...discover... */ }
if (core_mode != "jit" && !module_path.empty())
  config.module = moderngekko::ModuleSource::DynamicPath(std::move(module_path));
```

With this in the runner, the launcher's Play just passes `--core <config.cpu_core>`
and there is no shim. See [04 - Runtime and launcher](04-runtime-and-launcher.md)
for the full `--core` path and the JIT/static split.

### The launcher starts the runner with SDL, capturing the log

```cpp
std::vector<std::string> args = {
    SiblingRunner(argv[0]).string(), "--game", current_game.string(),
    "--user-dir", user_directory.string(), "--core", config.cpu_core};
// ...netplay / savestate args...
// Redirect the runner's stdout+stderr into <user>/Logs/ModernGekko.log via
// SDL_CreateProcessWithProperties (SDL_PROCESS_STDIO_REDIRECT). The launcher
// hides its own window, SDL_WaitProcess, then kills the tree after a timeout.
```

The launcher writes `ModernGekko.log` on the Play path. A *direct* runner launch
(RecompLauncher `start`, or a dev script) writes diagnostics to **stderr**; capture
them by redirection if you need a persistent log. Do not add a shim just to tee.

### RecompLauncher manifest uses the same two executables

```json
"prepare": { "program": ["<Title>Recomp.exe"], "args": ["--extract", "{game}"],
             "label": "Extracting the game files from your disc", "timeout": 1200 },
"start":   { "program": ["<Title>RecompRunner.exe"],
             "args": ["--module", "{install}/g<ID>_recomp.dll",
                      "--user-dir", "{local}/<Title>Recomp"] }
```

`--extract` is headless, prints `progress 0..1` lines, extracts into `Game/`
beside the exe, and records the path in `default-game.txt` (so `start` needs no
`--game`). The custom launcher and the manifest must use the **same user dir,
module name and config path** — two paths means two support cases.

### CMake wiring

```cmake
set(MODERNGEKKO_RUNNER_OUTPUT_NAME "<Title>RecompRunner" CACHE STRING "" FORCE)
set(MODERNGEKKO_LAUNCHER_OUTPUT_NAME "<Title>Recomp"     CACHE STRING "" FORCE)
# attach the runner .rc to moderngekko-run (the real runtime), NOT to a shim
target_sources(moderngekko-run PRIVATE assets/runner.rc)
# NO add_executable(... runner-shim ...) target. NO separate core exe.
```

---

## 2. Anatomy of the launcher shell (ImGui + SDL3 renderer)

The shell is a single ImGui root window over an SDL3 renderer backend. Layout:

```
+--------------------------------------------------------------+
|  header: logo image + product title            (header_h)    |
+------------+-------------------------------------------------+
|  sidebar   |  content: one card per settings group           |
|  nav btns  |  +---------------------------+                  |
|  (PLAY,    |  | Card title (sentence case)|                  |
|  GRAPHICS, |  | rows of controls          |                  |
|  PERF,     |  +---------------------------+                  |
|  AUDIO,    |  +---------------------------+                  |
|  CONTROLLER)|  | next card ...             |                  |
|  status    |  +---------------------------+                  |
+------------+-------------------------------------------------+
```

Root window (covers the viewport, no chrome):

```cpp
const float S = scale;                       // DPI / size scale; multiply ALL sizes by S
ImGui::SetNextWindowPos(viewport->Pos);
ImGui::SetNextWindowSize(viewport->Size);
ImGui::Begin("##launcher_root", nullptr,
             ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_NoMove |
             ImGuiWindowFlags_NoSavedSettings |
             ImGuiWindowFlags_NoBringToFrontOnFocus | ImGuiWindowFlags_NoNavFocus);
ImDrawList* draw = ImGui::GetBackgroundDrawList();
```

Sidebar and content are `BeginChild` regions with `ImGuiWindowFlags_NoBackground`
(so the backdrop shows through). Cards are `BeginChild(id, ImVec2(0, height*S), 0,
ImGuiWindowFlags_NoScrollbar)`. Every dimension is `N * S`; fonts are loaded at
scaled sizes (`PushFont(font_bold, 16 * S)`).

---

## 3. The theme token system (what changes per title)

The theme is a small set of tokens. Change these and nothing else:

| Token | Where it lives | DOR2 example |
|---|---|---|
| Product / exe names | CMake `MODERNGEKKO_*_NAME` | "WWE Day of Reckoning 2 Recomp" |
| Window title | `MODERNGEKKO_DEFAULT_WINDOW_TITLE` | "WWE Day of Reckoning 2" |
| Disc identity | `MODERNGEKKO_REQUIRED_DISC_ID`, `..._DOL_SHA256` | `GW2E78`, `e47abf73…` |
| Accent colour | `style.Colors[SliderGrab/CheckMark]` + nav highlight | gold `(0.91, 0.71, 0.23)` |
| Ground / surface / ink | `style.Colors[WindowBg/ChildBg/Text]` | charcoal / off-white |
| Icon | `assets/*.ico` via `.rc` | SteamGridDB icon |
| Backdrop + logo art | `assets/sgdb/<title>_grid.png`, `_logo.png` | cover + wordmark |
| Manifest strings | `recomplauncher.json` `label`/`help`/`exit_codes` | per title |
| Player docs | `README.txt`, `PLAYERS.md`, release notes | per title |

### The house style (anti-slop)

The shared look is deliberately restrained. Apply these rules so a new theme
does not drift into the generic AI aesthetic:

- **One ground, one ink, one accent.** Charcoal ground, off-white text, a single
  accent (gold for DOR2). Do not add a second accent or a gradient palette.
- **Real cover art as the dominant image**, not a procedural gradient/bokeh. The
  procedural arena is only the *fallback* when no art is present.
- **Crisp corners.** Small rounding (`FrameRounding 4`, `ChildRounding 6`,
  `WindowRounding 0`). No soft pillowy cards.
- **Tone-step surfaces, not hairlines.** Cards are a slightly lighter tone than
  the ground; no thin gold borders, no glass/blur.
- **Sentence-case readable card titles**, not tiny tracked uppercase labels.
- **Flat buttons**, one hover/active tone step.

Example style block (DOR2):

```cpp
style.FrameRounding = 4.0f; style.ChildRounding = 6.0f; style.WindowRounding = 0.0f;
style.Colors[ImGuiCol_Text]        = ImVec4(0.95f, 0.93f, 0.88f, 1.00f); // ink
style.Colors[ImGuiCol_ChildBg]     = ImVec4(0.10f, 0.10f, 0.12f, 0.90f); // surface
style.Colors[ImGuiCol_SliderGrab]  = ImVec4(0.91f, 0.71f, 0.23f, 1.00f); // accent
style.Colors[ImGuiCol_CheckMark]   = ImVec4(0.91f, 0.71f, 0.23f, 1.00f);
style.Colors[ImGuiCol_Button]      = ImVec4(0.16f, 0.16f, 0.20f, 0.95f);
// ...hover/active are one tone step lighter...
```

---

## 4. The gotchas that actually block agents

Each of these cost real time in the DOR2 port. Symptom -> cause -> fix.

### 4.1 Card text sits flush against the box edges (no margins)

**Cause:** `PushStyleVar(ImGuiStyleVar_WindowPadding, ...)` has **no effect** on
these child windows. Pushing it looks correct and changes nothing.

**Fix:** inset the content with `Indent` + a cursor offset, and undo it on close:

```cpp
// begin_card
ImGui::PushStyleColor(ImGuiCol_ChildBg, ImVec4(0.10f, 0.10f, 0.12f, 0.90f));
ImGui::BeginChild(id, ImVec2(0, height * S), 0, ImGuiWindowFlags_NoScrollbar);
ImGui::Indent(16 * S);
ImGui::SetCursorPosY(ImGui::GetCursorPosY() + 12 * S);
// ...title + rows...

// end_card
ImGui::Unindent(16 * S);
ImGui::EndChild();
ImGui::PopStyleColor(1);
```

Do the same `Indent(16*S)` / `SetCursorPosY(+12*S)` ... `Unindent(16*S)` for the
sidebar. Verify with a window screenshot, not by reading the code.

### 4.2 ImGui assertion: "missing PopStyleVar" / condition 0

**Cause:** a `PushStyleVar`/`PushStyleColor`/`PushFont` without a matching pop.
The `begin_card`/`end_card` pair must balance exactly.

**Fix:** count every push and pop. If `begin_card` pushes one style color,
`end_card` pops one. If you add a `PushStyleVar`, add the `PopStyleVar`. (The
Indent approach in 4.1 avoids style-var pushes entirely, which is why it is
preferred.)

### 4.3 Background goes black when the window is enlarged

**Cause:** drawing the full-window backdrop with ImGui `AddImage` on a draw list
is unreliable across resizes (clipping / stale viewport).

**Fix:** draw the backdrop with **SDL directly, after `SDL_RenderClear` and
before `ImGui_ImplSDLRenderer3_RenderDrawData`**, cover-fit so it fills any size:

```cpp
SDL_SetRenderDrawColor(renderer, 18, 20, 28, 255);
SDL_RenderClear(renderer);
if (bg_tex) {
  float iw = 0, ih = 0; SDL_GetTextureSize(bg_tex, &iw, &ih);
  int ww = 0, wh = 0;   SDL_GetRenderOutputSize(renderer, &ww, &wh);
  if (iw > 0 && ih > 0 && ww > 0 && wh > 0) {
    const float sc = std::max(ww / iw, wh / ih);   // cover, not contain
    const float dw = iw * sc, dh = ih * sc;
    const SDL_FRect dst{(ww - dw) / 2, (wh - dh) / 2, dw, dh};
    SDL_RenderTexture(renderer, bg_tex, nullptr, &dst);
  }
  SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);
  SDL_SetRenderDrawColor(renderer, 8, 8, 12, 150);  // scrim keeps cards readable
  SDL_RenderFillRect(renderer, nullptr);
}
ImGui_ImplSDLRenderer3_RenderDrawData(ImGui::GetDrawData(), renderer);
SDL_RenderPresent(renderer);
```

Keep the procedural arena only as the `if (!bg_tex)` fallback. Verify by resizing
the window to 1600x1000 and capturing.

### 4.4 Ninja does not recompile the launcher (your edits "do nothing")

**Cause:** Ninja sometimes fails to notice `moderngekko_launcher.cpp` changed, so
you keep running a stale binary and conclude your fix failed.

**Fix:** delete the object file to force a recompile, then build:

```powershell
Remove-Item build\moderngekko\moderngekko-runtime\CMakeFiles\moderngekko-launcher.dir\tools\moderngekko_launcher.cpp.obj -Force
# same for moderngekko-run.dir\tools\moderngekko_run.cpp.obj when you edit the runner
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

Confirm the build log actually shows `Building CXX ... moderngekko_launcher.cpp.obj`.

### 4.5 Link fails with LNK1104 (cannot open ...exe)

**Cause:** a running launcher/runner is locking the executable.

**Fix:** kill it before linking:

```powershell
Get-Process <Title>Recomp,<Title>RecompRunner -ErrorAction SilentlyContinue | Stop-Process -Force
```

### 4.6 `git apply` says "No valid patches in input"

**Cause:** Windows PowerShell 5.1 `>` redirection writes **UTF-16**, which
`git apply` cannot read. A patch generated with `git diff > file.patch` in
PowerShell is silently broken.

**Fix:** generate the patch with raw bytes (cmd redirection) and verify it:

```powershell
cmd /c "git -C lib\ModernGekko-Template\lib\ModernGekko diff > patches\moderngekko-settings.patch"
git -C lib/ModernGekko-Template/lib/ModernGekko apply --reverse --check ..\..\..\..\patches\moderngekko-settings.patch
# exit 0 == the patch applies cleanly to the pinned submodule
```

### 4.7 `add_custom_command(TARGET ...)` fails from the top-level CMake

**Cause:** the launcher is a target in a *subdirectory*; you cannot attach a
custom command to it from the top-level `CMakeLists.txt`.

**Fix:** copy static art at configure time with `file(COPY ... DESTINATION
${CMAKE_BINARY_DIR})` instead of a post-build custom command.

### 4.8 Edit tool "could not find oldString" on submodule files

**Cause:** the submodule working tree is LF; your match string used CRLF (or vice
versa), or whitespace differs.

**Fix:** match the file's actual line endings exactly; for large multi-line
replacements, normalize and rewrite via a small script rather than many fragile
edits.

### 4.9 A setting "does not work" after you added it

**Cause:** a stale runner silently ignores new config keys.

**Fix:** rebuild the runner and prove the option reached the runtime from the
`[video]` / `[audio]` log line (e.g. `aspect=... widescreen=...`). Never claim a
settings fix without that line.

---

## 5. Artwork loading

Load per-title art from next to the executable at startup; fall back to
procedural art when absent:

```cpp
SDL_Texture* bg_tex = nullptr;
if (SDL_Surface* s = SDL_LoadPNG((exe_dir / "<title>_grid.png").string().c_str())) {
  bg_tex = SDL_CreateTextureFromSurface(renderer, s);
  SDL_DestroySurface(s);
}
// same for <title>_logo.png -> logo_tex (drawn in the header)
```

Ship the PNGs in the package and copy them next to the launcher at configure
time (`file(COPY)`). Document the art source and license in `docs/ASSETS.md`.
SteamGridDB art is copyrighted; shipping it publicly requires the project
owner's explicit decision (DOR2 has one). Default policy is original art only.

---

## 6. Config and CLI surface

The shell uses a non-optional config API (`frontend_config.{hpp,cpp}`):
`LoadConfig` returns a struct-or-error, `ParseConfig` validates a candidate
string, `SaveConfig` round-trips. The launcher exposes a scriptable CLI that
uses the *same* validating parser as the GUI:

- `--extract <iso>` — headless extraction with `progress` lines (RecompLauncher).
- `--set key=value` — rewrite a config key, revalidate, save (no GUI needed).
- `--play` — load the default game and start the runner immediately.

Keep these identical across titles; they are shell features, not theme.

---

## 7. Build and verify recipe

```powershell
# build (force launcher/runner recompile if Ninja stalls)
powershell -ExecutionPolicy Bypass -File scripts\build.ps1

# prove both cores on the SINGLE runner (automation dir gives status.txt)
#   --core jit    -> booted=1, vps ~59.94
#   --core static -> [staticrecomp] module loaded, fallback=0, smc_failed=0

# prove the launcher flow
#   <Title>Recomp.exe --extract <iso>   (headless, progress 1.000)
#   <Title>Recomp.exe --play            (spawns the runner; check the log)

# package + verify (layout, icons, game-data scan, schema, staged prepare+run)
powershell -ExecutionPolicy Bypass -File scripts\package.ps1 -Version <v>
powershell -ExecutionPolicy Bypass -File work\verify-package.ps1 -Version <v>
```

A change is not done until the runner boots from the module and the log shows
`fallback=0`, `smc_failed=0`, no new crash, and the target rate (59.94) on the
reference scene. Screenshot the launcher at two sizes to prove margins and the
resize-safe backdrop.

---

## 8. Per-title theming checklist

- [ ] Copied the current shell; no logic fork.
- [ ] Two executables only: launcher + single runner (native `--core`). No shim,
      no `RunnerCore`, no `Play.cmd`, no shipped `Prepare.exe`.
- [ ] CMake names, disc ID, DOL hash set; runner `.rc` on `moderngekko-run`.
- [ ] Manifest `prepare` = launcher `--extract`; `start` = single runner; same
      user dir / module / config path as the launcher.
- [ ] Theme tokens swapped: names, title, accent, ground/ink, icon, grid/logo art.
- [ ] House style kept: one accent, real cover art, crisp corners, tone-step
      cards, sentence-case titles, flat buttons.
- [ ] Card/sidebar margins via `Indent` (4.1); style stack balanced (4.2).
- [ ] Backdrop drawn with SDL cover-fit (4.3); verified at a large size.
- [ ] Forced recompile (4.4); killed running exe before link (4.5).
- [ ] Patch is UTF-8 and `git apply --reverse --check` passes (4.6).
- [ ] Both cores verified; `[video]`/`[audio]` lines prove settings (4.9).
- [ ] Theme audit: no other title's name, icon, disc ID or strings anywhere.
- [ ] `LICENSES/` shipped; art source/license documented; game-data scan clean.

Record it in `STATE.md` as
`Launcher: shell <revision>, theme <title>, parity <date>`.
