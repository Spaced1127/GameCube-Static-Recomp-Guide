#!/usr/bin/env python3
"""GameCube disc / DOL / FST inspection and extraction.

Usage:
    python tools/gcdisc.py info    <game.iso>
    python tools/gcdisc.py list    <game.iso> [path-filter]
    python tools/gcdisc.py extract <game.iso> <out-dir> [path-filter]
    python tools/gcdisc.py dol     <game.iso> <out-dir>

The DOL is written section-by-section with a JSON manifest so it can be
loaded into a disassembler at the original virtual addresses.
"""
from __future__ import annotations

import json
import struct
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

GC_MAGIC = 0xC2339F3D
DOL_HEADER_SIZE = 0x100


@dataclass
class DolSection:
    kind: str
    index: int
    file_offset: int
    address: int
    size: int

    @property
    def end_address(self) -> int:
        return self.address + self.size


@dataclass
class Dol:
    sections: list[DolSection]
    bss_address: int
    bss_size: int
    entry_point: int

    @property
    def text_sections(self) -> list[DolSection]:
        return [s for s in self.sections if s.kind == "text"]

    @property
    def data_sections(self) -> list[DolSection]:
        return [s for s in self.sections if s.kind == "data"]


@dataclass
class FstEntry:
    name: str
    is_dir: bool
    offset: int = 0
    size: int = 0
    children: list["FstEntry"] | None = None


def parse_dol(data: bytes, file_offset: int = 0) -> Dol:
    hdr = data[file_offset:file_offset + DOL_HEADER_SIZE]
    if len(hdr) != DOL_HEADER_SIZE:
        raise ValueError("truncated DOL header")

    sections: list[DolSection] = []
    # DOL header: text offsets, data offsets, text addresses, data addresses,
    # text sizes, data sizes (not interleaved per section).
    for i in range(7):
        off, = struct.unpack_from(">I", hdr, i * 4)
        size, = struct.unpack_from(">I", hdr, 0x90 + i * 4)
        addr, = struct.unpack_from(">I", hdr, 0x48 + i * 4)
        if size:
            sections.append(DolSection("text", i, off, addr, size))
    for i in range(11):
        off, = struct.unpack_from(">I", hdr, 0x1C + i * 4)
        size, = struct.unpack_from(">I", hdr, 0xAC + i * 4)
        addr, = struct.unpack_from(">I", hdr, 0x64 + i * 4)
        if size:
            sections.append(DolSection("data", i, off, addr, size))
    bss_addr, bss_size, entry = struct.unpack_from(">III", hdr, 0xD8)
    return Dol(sections, bss_addr, bss_size, entry)


def read_dol(iso: Path) -> tuple[Dol, bytes]:
    with iso.open("rb") as f:
        f.seek(0x420)
        dol_offset = struct.unpack(">I", f.read(4))[0]
        f.seek(dol_offset)
        hdr = f.read(DOL_HEADER_SIZE)
        dol = parse_dol(hdr)
        image = bytearray()
        data = bytearray()
        max_end = max((s.file_offset + s.size for s in dol.sections), default=0)
        f.seek(dol_offset)
        raw = f.read(max_end)
        for s in dol.sections:
            chunk = raw[s.file_offset:s.file_offset + s.size]
            if len(chunk) != s.size:
                raise ValueError(f"DOL section {s.kind}{s.index} truncated")
            if s.kind == "text":
                image.extend(chunk)
            data.extend(chunk)
        return dol, bytes(raw)


def parse_fst(iso: Path) -> tuple[list[FstEntry], int, int]:
    with iso.open("rb") as f:
        f.seek(0x424)
        fst_offset = struct.unpack(">I", f.read(4))[0]
        fst_size = struct.unpack(">I", f.read(4))[0]
        f.seek(fst_offset)
        fst = f.read(fst_size)
    if len(fst) < 12:
        raise ValueError("FST too small")

    root_word, root_field1, root_field2 = struct.unpack_from(">III", fst, 0)
    root_type = root_word >> 24
    if root_type != 1:
        raise ValueError("FST root is not a directory")

    if (root_word & 0x00FFFFFF) == 0 and 0 < root_field2 <= len(fst) // 12:
        # Compact indexed FST used by this title. Each entry is 12 bytes:
        #   word0 = (type << 24) | name_offset   (type 1 = directory)
        #   dir:  word1 = parent index, word2 = next index (end of subtree)
        #   file: word1 = absolute file offset, word2 = size
        # Names live in a string table after the entry array.
        count = root_field2
        string_table = count * 12

        def name_at(off: int) -> str:
            start = string_table + off
            end = fst.find(b"\x00", start)
            return fst[start:end].decode("shift_jis", errors="replace")

        def parse_entry(index: int) -> tuple[FstEntry, int]:
            word, field1, field2 = struct.unpack_from(">III", fst, index * 12)
            typ, name_off = word >> 24, word & 0x00FFFFFF
            if typ == 1:
                entry = FstEntry(name_at(name_off), True, children=[])
                child = index + 1
                while child < field2:
                    sub, child = parse_entry(child)
                    entry.children.append(sub)
                return entry, field2
            return FstEntry(name_at(name_off), False, field1, field2), index + 1

        root, _ = parse_entry(0)
        return root.children or [], fst_offset, fst_size

    # Textbook GameCube FST: four u32 fields per entry.
    def name_at(off: int) -> str:
        end = fst.find(b"\x00", off)
        return fst[off:end].decode("shift_jis", errors="replace")

    def parse_dir(index: int) -> tuple[FstEntry, int]:
        _, name_off, _, next_off = struct.unpack_from(">IIII", fst, index * 12)
        entry = FstEntry(name_at(name_off), True, children=[])
        child = index + 1
        end = next_off // 12 if next_off else len(fst) // 12
        while child < end:
            typ, n_off, file_off, file_size = struct.unpack_from(">IIII", fst, child * 12)
            if typ == 1:
                sub, child = parse_dir(child)
                entry.children.append(sub)
            else:
                entry.children.append(
                    FstEntry(name_at(n_off), False, file_off, file_size)
                )
                child += 1
        return entry, end

    root, _ = parse_dir(0)
    return root.children or [], fst_offset, fst_size


def walk(entries: list[FstEntry], prefix: str = ""):
    for e in entries:
        path = f"{prefix}/{e.name}" if prefix else e.name
        if e.is_dir:
            yield path + "/", e
            yield from walk(e.children or [], path)
        else:
            yield path, e


def open_section(iso: Path, dol: Dol, section: DolSection) -> bytes:
    with iso.open("rb") as f:
        f.seek(0x420)
        dol_offset = struct.unpack(">I", f.read(4))[0]
        f.seek(dol_offset + section.file_offset)
        return f.read(section.size)


def cmd_info(iso: Path):
    with iso.open("rb") as f:
        hdr = f.read(0x440)
        f.seek(0x440)
        bi2 = f.read(0x40)
    magic, = struct.unpack_from(">I", hdr, 0x1C)
    dol_off, fst_off, fst_size, fst_max = struct.unpack_from(">IIII", hdr, 0x420)
    title = hdr[0x20:0x60].split(b"\x00")[0].decode("shift_jis", errors="replace")
    dol, _ = read_dol(iso)
    root, _, _ = parse_fst(iso)
    files = list(walk(root))

    print(f"File:        {iso}")
    print(f"Size:        {iso.stat().st_size:,} bytes")
    print(f"Game ID:     {hdr[0:6].decode('ascii', errors='replace')}")
    print(f"Title:       {title}")
    print(f"Magic:       {magic:#010x} {'(GameCube)' if magic == GC_MAGIC else '(unexpected)'}")
    print(f"Country:     {bi2[0x18]:#04x}")
    print(f"DOL offset:  {dol_off:#x}")
    print(f"FST offset:  {fst_off:#x}  size {fst_size:#x}")
    print(f"Entry point: {dol.entry_point:#010x}")
    print(f"BSS:         {dol.bss_address:#010x} + {dol.bss_size:#x}")
    print("DOL sections:")
    for s in dol.sections:
        print(f"  {s.kind:4} {s.index:2}  file {s.file_offset:#08x}  "
              f"mem {s.address:#010x}-{s.end_address:#010x}  size {s.size:#x}")
    print(f"FST entries: {len(files)}")

    # Summary of top-level directories and file count by extension.
    exts: dict[str, int] = {}
    for path, e in files:
        if not e.is_dir:
            ext = Path(path).suffix.lower() or "<none>"
            exts[ext] = exts.get(ext, 0) + 1
    top = sorted(exts.items(), key=lambda kv: -kv[1])[:20]
    print("Top extensions:")
    for ext, count in top:
        print(f"  {ext:12} {count}")


def cmd_list(iso: Path, filt: str | None):
    root, _, _ = parse_fst(iso)
    for path, e in walk(root):
        if filt and filt.lower() not in path.lower():
            continue
        if e.is_dir:
            print(f"{'d':1} {0:12}  {path}")
        else:
            print(f"{'-':1} {e.size:12}  {path}")


def cmd_extract(iso: Path, out_dir: Path, filt: str | None):
    root, _, _ = parse_fst(iso)
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    total = 0
    with iso.open("rb") as f:
        for path, e in walk(root):
            if e.is_dir:
                continue
            if filt and filt.lower() not in path.lower():
                continue
            dest = out_dir / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            f.seek(e.offset)
            data = f.read(e.size)
            if len(data) != e.size:
                raise ValueError(f"truncated file {path}")
            dest.write_bytes(data)
            count += 1
            total += e.size
    print(f"Extracted {count} files ({total:,} bytes) to {out_dir}")


def cmd_dol(iso: Path, out_dir: Path):
    dol, _ = read_dol(iso)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "entry_point": dol.entry_point,
        "bss_address": dol.bss_address,
        "bss_size": dol.bss_size,
        "sections": [],
    }
    for s in dol.sections:
        data = open_section(iso, dol, s)
        name = f"{s.kind}{s.index:02d}_{s.address:08x}.bin"
        (out_dir / name).write_bytes(data)
        manifest["sections"].append({**asdict(s), "file": name})
    (out_dir / "dol.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {len(dol.sections)} DOL sections to {out_dir}")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__.strip())
        return 2
    cmd, iso = argv[1], Path(argv[2])
    if cmd == "info":
        cmd_info(iso)
    elif cmd == "list":
        cmd_list(iso, argv[3] if len(argv) > 3 else None)
    elif cmd == "extract":
        if len(argv) < 4:
            print("extract needs an output directory")
            return 2
        cmd_extract(iso, Path(argv[3]), argv[4] if len(argv) > 4 else None)
    elif cmd == "dol":
        if len(argv) < 4:
            print("dol needs an output directory")
            return 2
        cmd_dol(iso, Path(argv[3]))
    else:
        print(f"unknown command {cmd!r}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
