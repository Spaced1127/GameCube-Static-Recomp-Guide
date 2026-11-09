# Tools

Generic GameCube disc/DOL helpers used by the case studies. They do not
contain game data.

| Tool | Purpose |
|---|---|
| `gcdisc.py` | Read/inspect a GameCube ISO, list/extract the FST, write the DOL with section addresses |
| `rvz_extract.py` | Convert a GameCube RVZ to ISO (Zstd/none/padding; no Wii partitions) |
| `verify_dol.py` | Compare every `main.dol` copy against the disc |
| `dol_disasm.py` | Disassemble a DOL at a virtual address with Capstone |
| `validate_manifest.py` | Validate RecompLauncher manifests against the SDK schema |

## Examples

```powershell
python tools/gcdisc.py info work\disc\game.iso
python tools/gcdisc.py list work\disc\game.iso
python tools/gcdisc.py extract work\disc\game.iso work\game
python tools/gcdisc.py dol work\disc\game.iso work\game
python tools/rvz_extract.py work\disc\game.rvz work\disc\game.iso
python tools/verify_dol.py work\disc\game.iso work\game\sys\main.dol
python tools/dol_disasm.py work\disc\main.dol 0x80003140 0x80003200
python tools/validate_manifest.py docs\recomplauncher.schema.json `
  examples\spongebob\recomplauncher.json
```

Requirements: Python 3, Capstone for `dol_disasm.py`, `jsonschema` for
`validate_manifest.py` (`pip install capstone jsonschema`).

These scripts are distributed under GPL-3.0 with the rest of this guide.
They are diagnostic helpers, not a substitute for Dolphin's disc conversion
and verification.
