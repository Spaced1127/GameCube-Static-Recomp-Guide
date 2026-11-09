# Project state

Updated: 2026-11-08

## Latest verified result

The standalone PC app runs the real game end to end:

- Asset-free launcher, runner and recompiled module (no disc data).
- Built-in ISO and RVZ import; extracted `main.dol` is byte-identical.
- Actual levels load: bedroom intro with dialogue, pants pickup, bedroom ->
  living room transition, full HUD, Gary NPC, all at ~60 fps.
- Pause menu, Options, Save Game, Load Game and the memory card all work:
  `78-GSQE-SpongeBob RFD.gci` is written and read back by the game.
- Intro/logo movies now run at **1.00x** (previously 0.41x) with continuous
  48 kHz audio; the fix is cross-chunk direct calls in the C generator.
- Gameplay: 59.7 fps / 0.995 (PGO + x86-64-v3 module).
- Graphical launcher: PLAY / GRAPHICS / PERFORMANCE / AUDIO / CONTROLLER pages,
  animated underwater backdrop, custom fonts, all options persisted.
- Audio mute + master volume in the launcher; mute reaches the backend
  (`MAIN_AUDIO_MUTED`, volume 0). Unlock-frame-rate toggle on PERFORMANCE.
- Release: `dist/SpongeBobRecomp-Release.zip`, no game data.

Open verification item: automated input did not cover the main menu's
flower-mat interaction. The game itself is unchanged; levels, pause/save menus
and the memory card work normally. A human playthrough should exercise the
menu path and the full story.

Evidence: `work/evidence/20..24-*.png`, `docs/notes/05-test-log.md`,
`docs/notes/07-performance.md`.

## Goal

A standalone, asset-free Windows PC application for the GameCube release of
*SpongeBob SquarePants: Revenge of the Flying Dutchman* (`GSQE78`, USA), with
ISO/RVZ import, configurable graphics and 60 fps gameplay; a Nintendo Switch
homebrew port follows.

## Goal constraint

A native static recompilation cannot produce a byte-identical GameCube DOL:
the output is host code (x86-64 PE/ELF). The retail DOL is preserved
bit-identically and verified; see
[`notes/03-objective-and-identity.md`](notes/03-objective-and-identity.md).

## Confirmed facts

### Disc

- File used: `Nickelodeon SpongeBob SquarePants - Revenge of the Flying Dutchman (USA).rvz`
- RVZ container: v1.00.00, Zstandard level 19, 128 KiB chunks, 11,139 groups.
- ISO size: 1,459,978,240 bytes.
- Game ID: `GSQE78`.
- Title: `SpongeBob SquarePants ROTFD`.
- Country byte: `0x00` (USA).
- GameCube magic at `0x1C`: `0xC2339F3D`.
- DOL offset: `0x1EC00`; FST offset: `0x316000`, size `0x2722`.
- Entry point: `0x80003140`.
- DOL SHA-256: `dca4f72b57e8bf3f540e694f01cc23ef687d2b25028d974b67356e15f1c2e009`.

### DOL sections

| Section | File offset | Virtual range | Size |
|---|---:|---|---:|
| text0 | `0x000100` | `0x80003100`–`0x80005620` | `0x2520` |
| text1 | `0x002620` | `0x8001F2C0`–`0x80299920` | `0x27A660` |
| data0 | `0x27CC80` | `0x80005620`–`0x80015F60` | `0x10940` |
| data1 | `0x28D5C0` | `0x80015F60`–`0x8001F2C0` | `0x9360` |
| data2 | `0x296920` | `0x80299920`–`0x80299980` | `0x60` |
| data3 | `0x296980` | `0x80299980`–`0x802999A0` | `0x20` |
| data4 | `0x2969A0` | `0x802999A0`–`0x802AFBA0` | `0x16200` |
| data5 | `0x2ACBA0` | `0x802AFBA0`–`0x802F3460` | `0x438C0` |
| data6 | `0x2F0460` | `0x80373E40`–`0x80377540` | `0x3700` |
| data7 | `0x2F3B60` | `0x803781C0`–`0x8037B9A0` | `0x37E0` |

- BSS: `0x802F3460` + `0x84D54`.
- `data6` overlaps the BSS range; `data7` begins 12 bytes after BSS ends.
  Keep this in mind when constructing flat memory images.

### Engine and middleware

- **TotemTech Data v1.73**, `(c) 1999–2002 Kalisto Entertainment`.
- Big Sky Interactive credited in the executable.
- Nintendo **Dolphin SDK**: OS (`$Revision: 60 $`), DVD, VI, PAD, SI, AI, AR,
  ARQ, AX, DSP, CARD, FIO, GX modules are statically linked.
- **Embedded CPython** (2001 copyright; 1.5/1.6 compatibility text in the
  string table, so likely Python 2.1/2.2). Scripts are shipped as `.pyc`
  inside the TotemTech bigfiles.
- **TotemTech scripting** (`.tsc`, text): commands such as `OpenBF`,
  `LoadObjectLib`, `Source`, `SetDBPath`, `DisplayImage`, `SBPlayLogoMovie`.
- Asset containers: `.dgc` (TotemTech Data bigfile, 78 files), manifests
  `.ngc` (78 files), speech `.sgc`, audio `.vag/.wav/.pcm*`, FMV `.h4m`
  (CRI) and `.thp` (Nintendo).

### Filesystem

GameCube FST is the standard 12-byte-entry format: the first word packs an
8-bit type and a 24-bit name offset; the string table follows the entry array.
Dolphin's `FileSystemGCWii.cpp` confirms this layout. Extracted tree contains
425 FST entries / 338 files (601,702,268 bytes).

Top-level: `DATA/`, `DB/`, `LevelTSC/`, `Speech/`, `Music/`, `Costumes/`,
`EXTRAS/`, `enums/`, `axdemo/`, `thpdemo/`, plus `Init.tsc`, `User.tsc`,
`Screens.tsc`.

### Boot flow

`User.tsc` drives the first seconds:

1. `SetBFPath .\.` + `EnableBF Read`.
2. `OpenBF DATA\SPONGE` → `Source Init.tsc` → `Source Script.tsc`.
3. `OpenBF DATA\PRELOAD` → `SBPreloadData`.
4. `Source Screens.tsc`: legal screen, Nick/THQ/Big Sky logo movies,
   "Hit Start" screen.

The DOL entry (`0x80003140`) performs standard SDK startup plus a relocation
pass over a table reached through `[0x800000F4]`, then calls the engine entry
at `0x801EC128` (likely `main`) and exits through `0x80120FB0`.

## Recompilation

DolRecomp generated `work/game`-independent output in
`build/recomp/generated`:

- text0: 2,376 instructions (733 known, 1,643 embedded data).
- text1: 649,624 instructions (649,469 known, 155 embedded data, 0 unknown).
- 160 C chunks, portable C backend.
- 261 "possible patching instruction" sites, mostly cache-management
  (`dcbst`/`icbi`) and SDK relocation writes. Full list in
  `build/recomp/generated/generated_smc.txt`; review any site that writes to
  `.text` before assuming it is benign.

## Runtime

ModernGekko (Dolphin-derived RecompCore) is the chosen runtime:

- Dolphin's `BootManager` boots `sys/main.dol` directly.
- A `StaticRecompModuleSource` feeds the recompiled module into the
  PowerPC core; HLE covers OS/DVD/GX/AI/AX/DSP/input.
- The same runtime can supply the virtual disc from `work/game/files`.

Build tree: `build/moderngekko` (CMake + Ninja + MSVC).

## Next actions


1. Script level transitions and a longer story playthrough (hub room, menus,
   pause, memory-card save) to extend coverage beyond the tested sections.
2. Listen to the Cubeb audio output on hardware; the DSP thread runs without
   errors but audio content was not auditioned here.
3. Netplay smoke test between two instances.
4. Nintendo Switch port after the PC app is stable.

## Known risks

- **Self-modifying code**: 261 flagged sites; most are cache ops, but any real
  text patch needs an explicit DolRecomp patch.
- **CPython runtime**: exceptions use `setjmp`/`longjmp` and computed state;
  the recompiled Python VM must preserve those semantics.
- **FIO / host file I/O**: the SDK includes `HOST_OPEN`; retail code may call
  it through debug paths. The runtime may need to map it to the virtual disc
  or stub it.
- **AX/DSP audio**: game uses AX + DSP; first boot should be headless/muted.
- **GX**: TotemTech uses display lists, TEV, possibly paletted textures and
  odd vertex formats; expect rendering work after boot.
- **Memory card / saves**: CARD module is linked; save UI may probe the card
  early.

## Commands

```powershell
# Extract the RVZ
python tools\rvz_extract.py "<disc>.rvz" work\disc\game.iso

# Inventory
python tools\gcdisc.py info  work\disc\game.iso
python tools\gcdisc.py list  work\disc\game.iso
python tools\gcdisc.py dol   work\disc\game.iso work\disc\dol

# Disassemble the entry point
python tools\dol_disasm.py work\disc\main.dol 0x80003140 0x80003300

# Recompile only (already done once)
build\dolrecomp\dolrecomp.exe --gamecube work\disc\main.dol build\recomp
```