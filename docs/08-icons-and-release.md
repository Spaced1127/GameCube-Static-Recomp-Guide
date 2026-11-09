# 08 - Icons and release

## Executable icons

Windows uses the first `ICON` resource in the PE. Add a multi-size `.ico` to
each executable. Keep the launcher and game icons distinct if you can:

- **Launcher**: app/game badge (e.g. circular character badge).
- **Game runner**: cover art or a full game icon.

### Make the ICO

Use a 1024x1024 PNG and save multiple sizes:

```python
from PIL import Image
img = Image.open("art.png").convert("RGB")
img.save("resources/icons/game.ico", format="ICO",
         sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
```

Windows will pick the right size for Explorer, taskbar and title bar.

### Embed with CMake/RC

`resources/icon.rc.in`:

```rc
101 ICON "@_moderngekko_icon_path@"
```

CMake helper:

```cmake
if(WIN32)
    function(moderngekko_add_executable_icon target icon_name)
        # Forward slashes matter: a Windows path in the generated .rc must
        # not turn \r, \n or \t into control characters.
        set(_moderngekko_icon_path
            "${CMAKE_CURRENT_SOURCE_DIR}/resources/icons/${icon_name}.ico")
        set(_moderngekko_icon_rc
            "${CMAKE_CURRENT_BINARY_DIR}/${target}-icon.rc")
        configure_file(
            "${CMAKE_CURRENT_SOURCE_DIR}/resources/icon.rc.in"
            "${_moderngekko_icon_rc}" @ONLY)
        target_sources(${target} PRIVATE "${_moderngekko_icon_rc}")
        set_source_files_properties("${_moderngekko_icon_rc}" PROPERTIES
            OBJECT_DEPENDS
            "${CMAKE_CURRENT_SOURCE_DIR}/resources/icons/${icon_name}.ico")
    endfunction()
endif()
```

Call it after each target:

```cmake
add_executable(moderngekko-run ...)
if(WIN32)
    moderngekko_add_executable_icon(moderngekko-run game)
endif()

add_executable(moderngekko-launcher ...)
if(WIN32)
    moderngekko_add_executable_icon(moderngekko-launcher launcher)
endif()
```

The `rc.exe` path is available from the MSVC/Windows SDK toolchain. Do not
use `file(TO_NATIVE_PATH ...)` in the generated `.rc`; forward slashes avoid
the `\r` bug.

### Verify

```powershell
Add-Type -AssemblyName System.Drawing
$icon = [System.Drawing.Icon]::ExtractAssociatedIcon("path\to.exe")
$icon.ToBitmap().Save("extracted.png", [System.Drawing.Imaging.ImageFormat]::Png)
```

Open `extracted.png` and confirm it is the intended art, not a blank/default
icon. Do this for both executables and for the downloaded release asset.

## Release package

A stable packaging script should:

1. Copy the launcher, runner, module and `Sys/` into a clean folder.
2. Copy `README.txt`, `PLAYERS.md`, licenses and `recomplauncher.json`.
3. Validate `recomplauncher.json` (JSON at minimum; schema in CI).
4. Refuse to package if `recomplauncher.json` is missing/invalid.
5. Refuse to package game data:
   - ISO/RVZ/WBFS/GCM/DOL/GCI/raw
   - `main.dol`, `boot.bin`, `bi2.bin`, `fst.bin`, `apploader.img`
   - any `Game/` directory
6. Print file count/size for the release report.
7. Zip with `Compress-Archive` or 7-Zip.
8. Compute SHA-256 and write `SHA256SUMS.txt`.

Asset name:

```text
SpongeBobRecomp-v0.1.3-Windows-x64.zip
```

Use the OS/arch words RecompLauncher recognizes. Put the manifest at the top,
next to the executable.

## Release notes

Include:

- what changed, with the user-visible effect
- performance numbers (before/after, target)
- the exact asset name and SHA-256
- no-game-data statement
- known limitations (RVZ, static vs JIT, external GPU load)
- if replacing a release, say so explicitly

## Publish and verify

```powershell
gh release create vX.Y.Z `
  "dist\MyRecomp-vX.Y.Z-Windows-x64.zip" `
  "dist\SHA256SUMS.txt" `
  --title "MyRecomp vX.Y.Z" `
  --notes-file dist\release-notes-vX.Y.Z.md
```

Then download the uploaded asset back:

```powershell
gh release download vX.Y.Z --pattern "MyRecomp-vX.Y.Z-Windows-x64.zip" --dir work\verify
Get-FileHash work\verify\*.zip -Algorithm SHA256
Expand-Archive work\verify\*.zip work\verify\unzipped
```

Verify:

- hash matches
- `recomplauncher.json` at the top
- schema validation passes
- both executable icons extract correctly
- `Sys/GameSettings/<ID>.ini` present if needed
- no game data in the zip
- release is marked latest, not draft/pre-release unless intended

## Same-tag caveat

Deleting and recreating the same tag is useful for a quick correction, but
existing RecompLauncher installs may not treat it as an update. For a real
player-facing update, bump the version (`v0.1.4`) and publish a new release.
Document the replacement in the release notes if you reuse a tag.

## Release checklist

- [ ] Build from documented commands.
- [ ] Launcher + runner icons embedded and verified.
- [ ] Manifest at top level; schema 0 errors.
- [ ] `prepare` headless progress works.
- [ ] Start works from a fresh install.
- [ ] Settings write to the right file and take effect.
- [ ] Saves/logs folders correct.
- [ ] No game data in the zip.
- [ ] SHA-256 computed and published.
- [ ] Asset downloaded back and verified.
- [ ] README/CHANGELOG/release notes match the asset.
- [ ] User approved commit/tag/release.
