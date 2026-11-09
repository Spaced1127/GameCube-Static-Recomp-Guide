# Templates

Copy these into a project and replace every placeholder.

| File | Use |
|---|---|
| `recomplauncher.template.json` | Starting RecompLauncher manifest; replace name/repo/disc ID/paths/Redump values. Validate with `tools/validate_manifest.py`. |
| `icon.rc.in` | RC resource for an embedded `.ico`. |
| `cmake-icon-helper.cmake` | CMake function that generates the RC and adds it to a target. |
| `game-settings-idle.ini` | `StaticRecompIdlePC` example; only use a real wait loop. |
| `build-module-pgo.ps1` | PGO workflow skeleton; adjust source/build paths and flags. |
| `make_release.example.ps1` | Packaging skeleton with manifest validation and game-data refusal. |
| `automation/README.md` | Runner automation directory/commands. |
| `automation/status-fields.md` | `status.txt` evidence fields. |
| `AGENTS.project.md` | Per-project agent rules. |
| `STATE.project.md` | Per-project state/ledger. |

The `.ps1` files are examples, not drop-in scripts: paths and CMake target
names vary by template version. Keep the safety checks (manifest validation,
no game data, SHA-256) when adapting them.

Never put a real game dump, DOL, texture, audio file or cover art in this
repository or a release.
