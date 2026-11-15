#!/usr/bin/env python3
"""Native RVZ (Dolphin compressed disc image) reader and ISO exporter.

Implements the WIA-derived RVZ container documented in Dolphin's
docs/WiaAndRvz.md and the GameCube raw-data path used by WIABlob.cpp.
Only the compression modes needed for this project are implemented:
Zstandard, None, and RVZ padding packing. Wii partition data is not
supported (this is a GameCube disc).

The reader exposes a random-access ISO byte view, so tools can inspect or
extract files without writing a 1.4 GB intermediate image.

Usage:
    python tools/rvz_extract.py input.rvz output.iso
"""
from __future__ import annotations

import struct
import sys
from collections import OrderedDict
from pathlib import Path

import zstandard

RVZ_MAGIC = b"RVZ\x01"
WIA_DISC_OFFSET = 0x48
DISC_HEADER_SIZE = 0x80
COMPRESSION_NONE = 0
COMPRESSION_ZSTD = 5

MASK32 = 0xFFFFFFFF
LFG_K = 521
LFG_J = 32
LFG_SEED_WORDS = 17
LFG_BYTES = LFG_K * 4
BLOCK_SIZE = 0x8000


class LaggedFibonacciGenerator:
    """Dolphin's GC/Wii disc padding PRNG (LaggedFibonacciGenerator.cpp)."""

    def __init__(self, seed: bytes):
        if len(seed) != LFG_SEED_WORDS * 4:
            raise ValueError(f"bad LFG seed size: {len(seed)}")
        self.buffer = [0] * LFG_K
        for i in range(LFG_SEED_WORDS):
            self.buffer[i] = struct.unpack_from(">I", seed, i * 4)[0]

        for i in range(LFG_SEED_WORDS, LFG_K):
            self.buffer[i] = (
                (self.buffer[i - 17] << 23)
                ^ (self.buffer[i - 16] >> 9)
                ^ self.buffer[i - 1]
            ) & MASK32

        # Dolphin folds the "shift by 18 instead of 16" output quirk into the
        # words and byte-swaps them so GetBytes can just memcpy native order.
        for i in range(LFG_K):
            x = self.buffer[i]
            x = (x & 0xFF00FFFF) | ((x >> 2) & 0x00FF0000)
            self.buffer[i] = x
        self.pos = 0
        for _ in range(4):
            self._forward()

    def _forward(self):
        b = self.buffer
        for i in range(LFG_J):
            b[i] ^= b[i + LFG_K - LFG_J]
        for i in range(LFG_J, LFG_K):
            b[i] ^= b[i - LFG_J]

    def skip(self, count: int):
        self.pos += count
        while self.pos >= LFG_BYTES:
            self._forward()
            self.pos -= LFG_BYTES

    def get(self, count: int) -> bytes:
        out = bytearray()
        while count:
            word = self.buffer[self.pos // 4]
            byte_in_word = self.pos % 4
            # Native little-endian memory after the Initialize byte swap is
            # the big-endian representation of the transformed word.
            raw = word.to_bytes(4, "big")
            take = min(count, 4 - byte_in_word)
            out += raw[byte_in_word:byte_in_word + take]
            self.pos += take
            count -= take
            if self.pos == LFG_BYTES:
                self._forward()
                self.pos = 0
        return bytes(out)


def unpack_rvz(stream: bytes, output_size: int, data_offset: int) -> bytes:
    """Decode Dolphin's RVZ packing (plain runs + PRNG runs)."""
    out = bytearray()
    p = 0
    while len(out) < output_size:
        if p + 4 > len(stream):
            raise ValueError("RVZ pack stream truncated while reading run size")
        size = struct.unpack_from(">I", stream, p)[0]
        p += 4
        junk = bool(size & 0x80000000)
        size &= 0x7FFFFFFF

        if junk:
            if p + LFG_SEED_WORDS * 4 > len(stream):
                raise ValueError("RVZ pack stream truncated while reading seed")
            lfg = LaggedFibonacciGenerator(stream[p:p + LFG_SEED_WORDS * 4])
            p += LFG_SEED_WORDS * 4
            lfg.skip(data_offset % BLOCK_SIZE)
            out += lfg.get(size)
        else:
            if p + size > len(stream):
                raise ValueError("RVZ pack stream truncated while reading plain run")
            out += stream[p:p + size]
            p += size
        data_offset += size

    if len(out) != output_size:
        raise ValueError(f"RVZ pack produced {len(out)} bytes, expected {output_size}")
    return bytes(out)


def read_compressed_table(f, offset: int, size: int, compression: int, expect: int) -> bytes:
    f.seek(offset)
    data = f.read(size)
    if len(data) != size:
        raise ValueError("compressed table truncated")
    if compression == COMPRESSION_ZSTD:
        data = zstandard.ZstdDecompressor().decompress(data, max_output_size=expect)
    elif compression != COMPRESSION_NONE:
        raise NotImplementedError(f"compression type {compression} is not supported")
    if len(data) < expect:
        raise ValueError(f"table decompressed to {len(data)}, expected at least {expect}")
    return data


class RvzReader:
    """Random-access ISO byte view of a Dolphin RVZ image.

    Group data is decompressed on first use and a small LRU cache keeps
    recently read groups. The file object can be used with seek/read/tell.
    """

    CACHE_GROUPS = 96

    def __init__(self, path: Path):
        self.path = Path(path)
        self._file = self.path.open("rb")
        self._cache: OrderedDict[tuple[int, int], bytes] = OrderedDict()
        self._pos = 0
        try:
            self._read_header()
        except Exception:
            self._file.close()
            raise

    def _read_header(self):
        f = self._file
        head = f.read(0x48)
        if len(head) != 0x48 or head[:4] != RVZ_MAGIC:
            raise ValueError("not an RVZ file")
        version, _compat, header2_size = struct.unpack_from(">III", head, 4)
        iso_size, file_size = struct.unpack_from(">QQ", head, 0x24)
        if self.path.stat().st_size != file_size:
            raise ValueError("RVZ file size does not match header")

        h2 = f.read(header2_size)
        if len(h2) != header2_size:
            raise ValueError("RVZ header2 truncated")
        disc_type, compression, _compr_level, chunk_size = struct.unpack_from(">IIII", h2, 0)
        if disc_type != 1:
            raise NotImplementedError(f"disc_type {disc_type} is not GameCube")
        if compression not in (COMPRESSION_NONE, COMPRESSION_ZSTD):
            raise NotImplementedError(f"compression type {compression} is not supported")
        if chunk_size % BLOCK_SIZE != 0:
            raise ValueError("invalid chunk size")

        self.version = version
        self.iso_size = iso_size
        self.chunk_size = chunk_size
        self.disc_header = h2[0x10:0x10 + DISC_HEADER_SIZE]

        p = 0x10 + DISC_HEADER_SIZE
        n_part, _part_t_size = struct.unpack_from(">II", h2, p)
        p += 8
        _part_off, = struct.unpack_from(">Q", h2, p)
        p += 8 + 20
        n_raw, = struct.unpack_from(">I", h2, p)
        p += 4
        raw_off, = struct.unpack_from(">Q", h2, p)
        p += 8
        raw_size, = struct.unpack_from(">I", h2, p)
        p += 4
        n_groups, = struct.unpack_from(">I", h2, p)
        p += 4
        group_off, = struct.unpack_from(">Q", h2, p)
        p += 8
        group_size, = struct.unpack_from(">I", h2, p)

        if n_part != 0:
            raise NotImplementedError("Wii partition entries are not supported")

        raw_table = read_compressed_table(f, raw_off, raw_size, compression, n_raw * 24)
        self._entries = []
        for i in range(n_raw):
            data_off, data_size, group_index, groups = struct.unpack_from(
                ">QQII", raw_table, i * 24
            )
            self._entries.append((data_off, data_size, group_index, groups))

        group_table = read_compressed_table(f, group_off, group_size, compression, n_groups * 12)
        self._groups = [
            struct.unpack_from(">III", group_table, i * 12) for i in range(n_groups)
        ]
        self.n_groups = n_groups

        # Entry data starts at data_off but Dolphin aligns the read down to a
        # 32 KiB sector and includes the skipped bytes in the group data.
        self._segments = []
        for entry_index, (data_off, data_size, group_index, groups) in enumerate(self._entries):
            skipped = data_off % BLOCK_SIZE
            aligned_off = data_off - skipped
            aligned_size = data_size + skipped
            for i in range(groups):
                this_chunk = min(chunk_size, aligned_size - i * chunk_size)
                if this_chunk <= 0:
                    break
                self._segments.append(
                    (
                        aligned_off + i * chunk_size,
                        aligned_off + i * chunk_size + this_chunk,
                        entry_index,
                        i,
                        aligned_size,
                        group_index + i,
                    )
                )
        if not self._segments:
            raise ValueError("RVZ has no raw data groups")

    def _get_group(self, group_in_entry: int, total_group: int, aligned_size: int) -> bytes:
        this_chunk = min(self.chunk_size, aligned_size - group_in_entry * self.chunk_size)
        key = (total_group, this_chunk)
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            return cached

        file_off4, group_data_size, packed_size = self._groups[total_group]
        compressed = bool(group_data_size & 0x80000000)
        group_data_size &= 0x7FFFFFFF
        if group_data_size == 0:
            chunk = bytes(this_chunk)
        else:
            self._file.seek(file_off4 * 4)
            raw = self._file.read(group_data_size)
            if len(raw) != group_data_size:
                raise ValueError(f"RVZ group {total_group} truncated")
            if compressed:
                dec = zstandard.ZstdDecompressor()
                if packed_size:
                    packed = dec.decompress(raw, max_output_size=packed_size)
                    if len(packed) != packed_size:
                        raise ValueError("packed group size mismatch")
                    chunk = unpack_rvz(packed, this_chunk, group_in_entry * self.chunk_size)
                else:
                    chunk = dec.decompress(raw, max_output_size=this_chunk)
            else:
                chunk = raw
                if packed_size:
                    chunk = unpack_rvz(chunk, this_chunk, group_in_entry * self.chunk_size)
            if len(chunk) != this_chunk:
                raise ValueError(
                    f"RVZ group {total_group}: got {len(chunk)} bytes, expected {this_chunk}"
                )

        self._cache[key] = chunk
        if len(self._cache) > self.CACHE_GROUPS:
            self._cache.popitem(last=False)
        return chunk

    def read_at(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0:
            raise ValueError("negative read")
        if offset >= self.iso_size or size == 0:
            return b""
        size = min(size, self.iso_size - offset)
        out = bytearray(size)
        end = offset + size

        # The extractor writes the disc header first, then group data on top.
        # Mirror that so a malformed/absent first group still yields the header.
        if offset < DISC_HEADER_SIZE:
            n = min(DISC_HEADER_SIZE - offset, size)
            out[:n] = self.disc_header[offset:offset + n]

        for seg_start, seg_end, _entry_index, group_in_entry, aligned_size, total_group in self._segments:
            if seg_end <= offset or seg_start >= end:
                continue
            copy_start = max(seg_start, offset)
            copy_end = min(seg_end, end)
            chunk = self._get_group(group_in_entry, total_group, aligned_size)
            chunk_start = copy_start - seg_start
            out[copy_start - offset:copy_end - offset] = chunk[
                chunk_start:chunk_start + (copy_end - copy_start)
            ]
        return bytes(out)

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._pos = offset
        elif whence == 1:
            self._pos += offset
        elif whence == 2:
            self._pos = self.iso_size + offset
        else:
            raise ValueError("invalid whence")
        return self._pos

    def tell(self) -> int:
        return self._pos

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = self.iso_size - self._pos
        data = self.read_at(self._pos, size)
        self._pos += len(data)
        return data

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def open_disc(path: Path):
    """Open an ISO or RVZ image as a seekable binary stream.

    RVZ is detected by magic, not by the filename extension.
    """
    path = Path(path)
    with path.open("rb") as probe:
        magic = probe.read(4)
    if magic == RVZ_MAGIC:
        return RvzReader(path)
    return path.open("rb")


def disc_size(path: Path) -> int:
    """Uncompressed disc size for an ISO or RVZ image."""
    path = Path(path)
    with path.open("rb") as probe:
        magic = probe.read(4)
    if magic == RVZ_MAGIC:
        with RvzReader(path) as reader:
            return reader.iso_size
    return path.stat().st_size


def image_kind(path: Path) -> str:
    path = Path(path)
    with path.open("rb") as probe:
        return "RVZ" if probe.read(4) == RVZ_MAGIC else "ISO"


def extract(rvz_path: Path, iso_path: Path):
    with RvzReader(rvz_path) as reader:
        print(f"RVZ v{reader.version >> 24}.{reader.version >> 16 & 0xff:02x}.{reader.version >> 8 & 0xff:02x}")
        print(f"ISO size: {reader.iso_size:,} bytes, chunk: {reader.chunk_size:,}, groups: {reader.n_groups:,}")
        total_groups = (reader.iso_size + reader.chunk_size - 1) // reader.chunk_size

        with iso_path.open("wb") as out:
            out.truncate(reader.iso_size)
            for index, offset in enumerate(range(0, reader.iso_size, reader.chunk_size), 1):
                chunk = reader.read_at(offset, min(reader.chunk_size, reader.iso_size - offset))
                out.seek(offset)
                out.write(chunk)
                if index % 256 == 0 or offset + len(chunk) == reader.iso_size:
                    done = offset + len(chunk)
                    pct = min(100, done * 100 // reader.iso_size)
                    print(f"\r  groups {index:,}/{total_groups:,}  {pct:3d}%", end="", flush=True)
        print()

    print(f"Wrote {iso_path} ({iso_path.stat().st_size:,} bytes)")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip())
        return 2
    extract(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
