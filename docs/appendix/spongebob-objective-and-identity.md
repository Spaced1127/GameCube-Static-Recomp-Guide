# Why "bit-identical rebuilt DOL" cannot coexist with a native static recomp

Updated: 2026-11-08

## The contradiction

A static recompiler changes the instruction set. DolRecomp reads the retail
PowerPC `main.dol` and emits C. The C is compiled by MSVC into an **x86-64
Windows shared library / executable**. That artifact:

- is not a GameCube DOL;
- has no PowerPC instructions except the preserved data;
- has a different header, section table, address space, and machine code.

Therefore "the rebuilt main executable (DOL) must be byte-for-byte identical
to the original retail file" is unsatisfiable for any static recompilation.
The only way to emit an identical DOL is to copy the input, which is not a
recompilation and does not produce a PC port.

The same applies to "every linked module": the linked modules are host
libraries (`.dll`), not GameCube relocatable modules (`.rel`).

## What can be proven, and is being proven

1. The retail DOL extracted from the disc is preserved exactly:
   - `work/disc/main.dol`
   - `work/game/sys/main.dol`
   - `build/modules/GSQE78/<hash>/dolrecomp-output/generated/main.dol`
   All three are compared to the bytes at ISO offset `0x1EC00` by
   `tools/verify_dol.py` (SHA-256, SHA-1, full byte diff).
   SHA-256: `dca4f72b57e8bf3f540e694f01cc23ef687d2b25028d974b67356e15f1c2e009`,
   zero differences.
2. The native artifact is demonstrably not a DOL:
   - `gGSQE78_recomp.dll`
   - 181,241,344 bytes
   - header `MZ`, PE machine `0x8664` (x86-64)
   - SHA-256 `903641f73aa4ca0c67151fdaa6dc258a6c19011580fb8635aab212d3a86f1a9d`
3. The recompiler is deterministic: the same input DOL and tool version
   produce the same generated C tree (hashes recorded per build).
4. The native port's behavior is tested against the retail ISO running in a
   GameCube emulator.

## What would satisfy a literal reading

Only one of these:

- change the success criterion to "the retail DOL is preserved bit-identically
  and the native port is behaviorally identical"; or
- define "rebuilt DOL" as a **recompiled PowerPC DOL** (a binary rewriter that
  reproduces the original instructions), which is a different project and is
  not a PC port; or
- accept a byte-identical **copy** of the DOL as the deliverable, which is not
  a static recompilation.

The project continues on the first interpretation, because it is the only one
that matches the stated goal: a native PC port, then a Switch port.

## Evidence commands

```powershell
python tools\verify_dol.py work\disc\game.iso `
    work\disc\main.dol work\game\sys\main.dol
```
