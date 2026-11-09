# 02 - Disc, DOL and Redump

## What is on a GameCube disc

A GameCube disc is **not ISO 9660**. The first bytes contain:

```text
0x0000  boot.bin        disc ID, game name, region, magic
0x0440  bi2.bin         debug/arena defaults
0x2440  apploader.img   boot loader
        main.dol         the PowerPC executable
        FST              file system table (files/ tree)
```

The extracted game should look like:

```text
Game/
  sys/
    boot.bin
    bi2.bin
    apploader.img
    main.dol
  files/
    ... all game files
```

The runner only needs `sys/main.dol` and `files/` for gameplay, but keep
`boot.bin`/`bi2.bin`/`apploader.img` in the extraction for completeness.

## Identify the game

Use `tools/gcdisc.py` or Dolphin's disc properties:

```powershell
python tools/gcdisc.py info work\disc\game.iso
```

Record:

- **Disc ID**: 6 characters, e.g. `GSQE78`, `GBQE78`.
- **Game name / region**.
- **DOL SHA-256**: the retail executable hash.
- **Redump size and CRC-32**: needed for RecompLauncher's verified badge.
- **Revision** if present.

The SpongeBob case:

```text
Disc ID:     GSQE78
Size:        1459978240
CRC-32:      f2facf74
DOL SHA-256: dca4f72b57e8bf3f540e694f01cc23ef687d2b25028d974b67356e15f1c2e009
```

The Rocket Power case:

```text
Disc ID: GBQE78
Size:    1459978240
CRC-32:  8be53ce8
```

Redump and GameTDB are the sources of truth. A size/CRC mismatch is a wrong
dump, a bad rip, or a different revision; do not "fix" it by disabling checks
in the runtime.

## Extract

```powershell
python tools/gcdisc.py extract work\disc\game.iso work\game
```

`gcdisc.py` reads the DOL header, FST and files without loading the whole
image. Use a path filter when you only need a subset for diagnosis:

```powershell
python tools/gcdisc.py list work\disc\game.iso
python tools/gcdisc.py extract work\disc\game.iso work\game "files/*.tsc"
```

The DOL can also be written with section addresses preserved:

```powershell
python tools/gcdisc.py dol work\disc\game.iso work\game
```

## RVZ / compressed images

```powershell
python tools/rvz_extract.py work\disc\game.rvz work\disc\game.iso
```

`rvz_extract.py` implements the GameCube path of Dolphin's WIA/RVZ container
(Zstandard, no compression, RVZ padding). It does not handle Wii partitions.
After extraction, verify the ISO size/CRC against Redump, then run `gcdisc.py`.

Dolphin's own **Convert File** dialog is the safest option for unusual RVZ
features. RecompLauncher's `game.kind: "iso"` may reject RVZ; see
[07-recomplauncher.md](07-recomplauncher.md).

## Verify the DOL

```powershell
python tools/verify_dol.py work\disc\game.iso work\game\sys\main.dol
```

The recompiler must consume the **retail** DOL. If the project patches the DOL
(e.g. a tournament patch or a native patch manifest), keep the original hash
and document both hashes:

- `MODERNGEKKO_REQUIRED_DOL_SHA256` = retail hash
- `MODERNGEKKO_ACCEPTED_SOURCE_DISC_ID` = clean disc ID
- `MODERNGEKKO_REQUIRED_DISC_ID` = patched/runtime disc ID

For most single-game recomp projects, use the retail DOL directly and require
the exact hash in the runner. Refuse a wrong region/revision with a clear
message.

## Disassemble a hot address

```powershell
python tools/dol_disasm.py work\disc\main.dol 0x8011EF00 0x8011EF90
```

The disassembler uses Capstone's PowerPC/Gekko mode. Use it to map a dispatch
sample or a crash PC back to the guest instruction stream.

## Redump entry for RecompLauncher

`game.dumps` takes the disc-level size and CRC-32:

```json
"dumps": [
  { "name": "USA", "size": 1459978240, "crc32": "f2facf74" }
]
```

The launcher reads the whole file anyway to check completeness, then compares
the CRC. A matching copy gets "Matches the verified USA disc"; a non-matching
copy still works, but without the badge. Do not refuse a non-matching copy just
because the badge is missing; the prepare step's disc-ID/DOL check is the
functional gate.

## GameCube-specific validation

The RecompLauncher SDK's `check` supports `file`, `xdvdfs` and `iso9660` only.
GameCube discs are not ISO 9660, so a GameCube manifest usually has **no
`check`**. Rely on:

- `game.dumps` (Redump size/CRC)
- `prepare` running `--extract`, which validates the disc ID and retail DOL
- the runner's `MODERNGEKKO_REQUIRED_DISC_ID` / `MODERNGEKKO_REQUIRED_DOL_SHA256`

The player picks the ISO manually. If your project accepts both ISO and an
extracted folder, use `kind: "iso_or_folder"` and `check.file: "sys/main.dol"`
(see the Rocket Power example).
