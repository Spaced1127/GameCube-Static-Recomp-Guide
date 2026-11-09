#!/usr/bin/env python3
"""Verify that every copy of the retail DOL is byte-identical to the disc.

A static recompiler consumes the retail DOL and emits host code. The emitted
executable/module is not a GameCube DOL, so "bit-identical rebuilt DOL" can
only be asserted for the preserved input, not for the native artifact.

Usage:
    python tools/verify_dol.py <game.iso> <main.dol> [more.dol ...]
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def first_diff(a: bytes, b: bytes) -> int | None:
    limit = min(len(a), len(b))
    for i in range(limit):
        if a[i] != b[i]:
            return i
    if len(a) != len(b):
        return limit
    return None


def extract_dol(iso: Path) -> bytes:
    with iso.open("rb") as f:
        f.seek(0x420)
        dol_off = struct.unpack(">I", f.read(4))[0]
        f.seek(dol_off)
        hdr = f.read(0x100)
        ends = []
        for i in range(7):
            off, = struct.unpack_from(">I", hdr, i * 4)
            size, = struct.unpack_from(">I", hdr, 0x90 + i * 4)
            if size:
                ends.append(off + size)
        for i in range(11):
            off, = struct.unpack_from(">I", hdr, 0x1C + i * 4)
            size, = struct.unpack_from(">I", hdr, 0xAC + i * 4)
            if size:
                ends.append(off + size)
        f.seek(dol_off)
        return f.read(max(ends))


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__.strip())
        return 2
    iso = Path(argv[1])
    reference = extract_dol(iso)
    print(f"reference: {iso} -> DOL {len(reference):,} bytes")
    print(f"  SHA-256 {sha256(reference)}")
    print(f"  SHA-1   {sha1(reference)}")
    ok = True
    for name in argv[2:]:
        path = Path(name)
        data = path.read_bytes()
        diff = first_diff(reference, data)
        same = diff is None
        print(f"\n{path}")
        print(f"  size    {len(data):,} {'OK' if len(data) == len(reference) else 'MISMATCH'}")
        print(f"  SHA-256 {sha256(data)} {'OK' if same else 'MISMATCH'}")
        print(f"  SHA-1   {sha1(data)} {'OK' if same else 'MISMATCH'}")
        if same:
            print("  byte diff: zero differences")
        else:
            print(f"  first difference at 0x{diff:x}")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
