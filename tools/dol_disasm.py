#!/usr/bin/env python3
"""Disassemble a GameCube main.dol by virtual address.

Usage:
    python tools/dol_disasm.py <main.dol> <start-hex> [end-hex] [count]

Sections and the entry point are read from the DOL header. Uses capstone's
PowerPC (Gekko-compatible) disassembler.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN


def load_sections(path: Path):
    data = path.read_bytes()
    hdr = data[:0x100]
    sections = []
    for i in range(7):
        off, = struct.unpack_from(">I", hdr, i * 4)
        size, = struct.unpack_from(">I", hdr, 0x90 + i * 4)
        addr, = struct.unpack_from(">I", hdr, 0x48 + i * 4)
        if size:
            sections.append((addr, addr + size, data[off:off + size], f"text{i}"))
    for i in range(11):
        off, = struct.unpack_from(">I", hdr, 0x1C + i * 4)
        size, = struct.unpack_from(">I", hdr, 0xAC + i * 4)
        addr, = struct.unpack_from(">I", hdr, 0x64 + i * 4)
        if size:
            sections.append((addr, addr + size, data[off:off + size], f"data{i}"))
    entry, = struct.unpack_from(">I", hdr, 0xE0)
    bss_addr, bss_size = struct.unpack_from(">II", hdr, 0xD8)
    return sections, entry, (bss_addr, bss_size)


def find(sections, addr: int):
    for start, end, data, name in sections:
        if start <= addr < end:
            return start, end, data, name
    return None


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__.strip())
        return 2
    path = Path(argv[1])
    sections, entry, bss = load_sections(path)
    start = int(argv[2], 0)
    end = int(argv[3], 0) if len(argv) > 3 else start + 0x100
    count = int(argv[4], 0) if len(argv) > 4 else None
    if start == 0:
        start = entry
        end = start + 0x100

    md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
    md.detail = False
    sec = find(sections, start)
    if not sec:
        print(f"{start:#x} is not in a DOL section")
        return 1
    sec_start, sec_end, data, name = sec
    pos = start - sec_start
    addr = start
    n = 0
    while addr < end and addr < sec_end:
        chunk = data[pos:pos + 4]
        if len(chunk) < 4:
            break
        for ins in md.disasm(chunk, addr):
            print(f"{ins.address:08x}  {ins.bytes.hex():8}  {ins.mnemonic:10} {ins.op_str}")
        pos += 4
        addr += 4
        n += 1
        if count is not None and n >= count:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
