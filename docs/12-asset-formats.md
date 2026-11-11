# 12 - Retail asset formats

A recomp does not need to understand the game's assets: the runtime hands the
game a virtual disc and the original code reads its own files. Asset work
becomes useful when you need to:

- prove the disc extraction is complete (every archive tile accounted for);
- explain a rendering bug (a black texture, a missing model, a stretched HUD);
- replace art or audio for a mod without touching the disc image;
- build a level/asset viewer or a second target (see
  [13-other-targets.md](13-other-targets.md));
- sanity-check what a game error message is actually complaining about.

This page is the method that worked across the projects, with the concrete
results from Rocket Power: Beach Bandits (`GBQE78`). Everything here was
derived from the retail DOL and the player's own extracted files. No asset,
archive or extracted tree belongs in Git.

## 1. Inventory before decoding

Count by extension and by magic, per directory, before writing a parser. It
answers "which container matters" in one pass:

```text
WMX8  (GW3E78): 5,266 files / 1.41 GB, 5,773 FST entries
  .yad 1,981   .tex 1,011   .ymg 732   .tpl 623   .pac 296   .ycg 163
WMXIX (GW9E78): .tex 1,783   .ymg 1,464   .yag 215   .ycg 184   .atr 167
  .pac 160     .wparry 64   .yad 41     .mpc 13    .tpl 9     .mpq 7
RPBB  (GBQE78): 11 files in the FST, 679 MB, one 516 MB pakfile.pak
```

Two patterns repeat:

- **One big archive plus loose files.** The large `.pak` holds almost
  everything; the FST only exposes the loader and the archive.
- **The extension is a hint, not a guarantee.** In RPBB, 207 files named
  `.tpl` are not TPL, and 410 files named `.obp` are not `OB11`. Always check
  magic bytes and record the hit rate.

Extension surveys also tell you the engine: Yukes titles ship `adm/`, `bg/`,
`model/`, `motion/`, `menu/`, `sound/` and `.ymg/.yad/.ycg` (CRI ADX family).

## 2. Archives: derive the layout, do not assume it

RPBB's `pakfile.pak` is a good general shape:

```text
0x00000000  u32   nameBlobLen
0x00000004  ...   NUL-terminated strings: directory paths, then file names
            ...   file record table    (8 bytes each: {u32 A; u32 B;})
            ...   record-table footer  (~40 bytes, end-of-table marker)
            ...   directory table      (20 bytes each)
            ...   zero padding
            ...   file data            (contiguous, in A order)
            ...   zero trailer         (4,096 bytes, not a file)
```

Derivation rules that avoided guesswork:

| Value | How it was found |
|---|---|
| record count | first `A[1] == 0` anchor; records ascend from there |
| data base | end of the zero run after the directory table (`0x106800`) |
| file offset | `data_base + A` |
| file size | `next_distinct_A - A` (padding included, still exact) |
| directory membership | `[firstRec, lastRec]` inclusive, disjoint ranges |
| names | by index into the string blob, not by pointer |

Validation is the part that matters. The extraction is correct when:

- `sum(size)` over all records equals the data region size **exactly**
  (RPBB: 515,110,656 bytes, zero holes);
- 96%+ of `.tpl` records start with the TPL magic, 86%+ of `.obp` with `OB11`,
  96%+ of `.bsc` with `BSC1`, 94%+ of `.ent` are ASCII text;
- the archive reader round-trips every path and matches the Python extractor
  byte-for-byte on a sample (RPBB: 400 sampled records, 55,768 paths).

Traps that cost time:

- **End-anchored name pointers cannot express names shorter than three
  characters.** RPBB's `Fx` directory points into the previous name; assigning
  names by table index fixes it.
- **Aliases share an offset.** 43 RPBB records point at the previous record's
  `A` (developer logs copied under two names). Write both names, zero length.
- **Record 0 is a header marker**, not a file. Its offset points back into the
  string blob and produces a negative size.
- **The trailer is not the last file.** Subtract it from the last record's
  span.
- **Case-insensitive collisions and Windows-invalid characters** need a
  rename map, recorded in the manifest, or NTFS silently loses files.

Write the reader once as portable C with no platform dependency, then a host
harness that validates it against the real archive. The same code can be the
shipping reader on another platform.

## 3. Textures

RPBB settled the scope by surveying all 5,462 `.tpl` records first:

| Finding | Detail |
|---|---|
| format | 5,255 / 5,255 decodable textures are **CMPR** (GX format `0x0E`) |
| dimensions | packed in one `u32`: high half = height, low half = width |
| data offset | absolute, not relative to the texture header |
| mipmaps | present; data is 4/3 of level 0 |
| non-TPL | 207 files with a `.tpl` name are text/other containers |

CMPR is DXT1 with two GX twists: 8x8 tiles holding four 4x4 sub-blocks in
TL/TR/BL/BR order, and big-endian colour and index words. Decode order:

1. re-order GX tiles into a DXT1 `.dds`;
2. byte-swap to little-endian;
3. decode with an independent implementation (Pillow).

Across 20 textures from 8x8 to 512x512 the C output was **bit-identical**
(MAD 0.00, max channel diff 0). That is the gate to demand before trusting a
decoder: not "it looks plausible", but zero difference against a reference.

Also check for engine-level variants:

- `__ALPHA__` suffixes and separate alpha sheets;
- chroma-key foliage (leaves are ~81% pure green, ~19% pure black at alpha
  255) — treat as a key only when the texture is nearly binary, or water and
  gradients break;
- paletted/CI textures in other engines are a different path entirely; the
  RPBB result says nothing about them.

## 4. Meshes

RPBB's `.obp` is `OB11`:

```text
0x00  "OB11"   0x04  u32 11 (version)   0x0C u32 kind (1/3/7)
0x20  block0: u32 size (=152), then triangleCount at +0x24
0xC0  block1: u32 size (=508), then (size-4)/12 records: {ptr, count, size}
      then stream 0..N, each `size` bytes, padded to 32
```

Two results worth reusing:

- **`+0x24` is the triangle count, not the vertex count.** Proof: the index
  stream has `3 x triangleCount` entries and the maximum index is below
  `rec1.count`. StreetLight: 142 triangles, 91 vertices, 426 indices, max 90.
- **Per-material triangle ranges tile the index list exactly.** Verified on
  2,692 of 2,693 meshes, no gaps or overlaps. A material without its own
  `TEXTURE` command inherits the previous one, so the material script is a
  state machine.

Stream indices are stable across files (position, UV, packed colour/normal,
16-bit indices, material tables, material script text, second UV, vertex
colour). Texture resolution order that matched the engine:

```text
<obp dir>\textures\<name>.tpl
<obp dir>\<name>.tpl
<parent>\textures\<name>.tpl
<parent>\<name>.tpl
archive-wide basename search (prefer Common_Assets)
then the __ALPHA__ variant pass
```

`BSC1` (`.bsc`) is a collision/visibility tree cache: the header is stable
(`"BSC1"`, version 14, triangle count at `+0x0C`, power-of-two at `+0x2C`), and
the engine regenerates it when missing. Do not block a port on decoding it.

## 5. Scenes: entities, transforms, manifests

Levels are text includes plus binary records, not a directory scan:

```text
environment.ent
  #include Lakes\Lakes_Hub\environment\Lks_Hub_lvl.ent
  #include Lakes\Lakes_Hub\Environment\Lks_Tre01.ent

Environment\Lks_Tre01
{
#binary Lakes\Lakes_Hub\environment\9.dbx
}
```

The `.dbx` key table came from the DOL string table:

```text
coordinate scale matrix mesh name clipped non_max_matrix no_scene_lighting
lightable render_last force_into_alphalist alpha_sort_priority type
roll pitch yaw Scale_x Scale_y Scale_z
```

Transform: `world = coordinate + R * (scale * local)`, with `R` row-major from
the three bracketed triples. Parse **by key name**, not by triple shape; field
order varies between files and the shape heuristic produced scale/position
swaps.

Then the level manifest decides what is drawable:

```text
chapter.chp
  1
  Lakes\Wavebike_Madness\environment\Lks_hub_Lvl_02.ob   <- collision, not drawn
  6
  Environment.ent  LevelObjects.ent  Sounds.ent  Buildings.ent
  AICharacters.ent  NoLoad.ent
```

Consequences:

- The first mesh in `chapter.chp` is **collision geometry**. Drawing it puts a
  second terrain over the real one.
- Entity type `0x55` is a clipform/trigger volume. Skip it; it draws as large
  flat sheets.
- `NoLoad.ent` is excluded by the engine.
- Some levels ship binary `.ent` blobs; fall back to every `.dbx` under the
  level directory instead of assuming text.

## 6. What this buys a recomp

| Task | Asset work that helps |
|---|---|
| "Texture is black" | confirm the name resolves in the engine's search order; check `__ALPHA__` variant and CMPR decode |
| "Something invisible is blocking" | find the clipform/trigger mesh and confirm it is skipped |
| "HUD stretched in 16:9" | separate 2D/3D assets; HUD is not part of the 3D projection |
| "Movie stutters" | check the container (`.thp` vs CRI `.h4m`/`.mp4`), then the runtime path |
| Mod support | replace a texture or sound file outside the disc, keep the archive index |
| Second target | portable reader + decoder is the part that survives a rewrite |
| Level viewer | compose from `.ent`/`.dbx`, not from a directory walk |

A flattened viewer mesh has limits worth knowing before debugging them: 16-bit
indices cap a level at 65,535 vertices (RPBB's `OSCommon\CBD` is already at
54,381), and foliage needs real alpha blending, not just alpha test.

## 7. Tooling rules

- **Host first.** Every parser has a host harness that prints counts and
  dumps a PPM/PNG. If it cannot be validated without the console, it is not
  validated.
- **Byte-exact validation.** Magic hit rates, exact tiling, round-trip paths,
  sampled byte comparison, decoder MAD 0.
- **Record the derails.** Short-name defect, aliases, record 0, trailer: these
  are format facts, not one-off bugs.
- **Keep game data out.** Extract into `work/`, hash the manifest, never commit
  the archive, the extracted tree, or a dumped texture.

## Acceptance

- [ ] Archive extraction tiles the data region exactly.
- [ ] Magic/extension agreement recorded per type.
- [ ] Decoder agrees bit-for-bit with an independent implementation.
- [ ] Material ranges tile the triangle list with no gaps.
- [ ] Scene composition matches what the runtime draws (no collision mesh, no
      clipforms).
- [ ] Everything reproducible from the player's own dump with a documented
      command.
