# Cheat sheet

## Disc / DOL

```powershell
python tools/gcdisc.py info work\disc\game.iso
python tools/gcdisc.py extract work\disc\game.iso work\game
python tools/gcdisc.py dol work\disc\game.iso work\game
python tools/verify_dol.py work\disc\game.iso work\game\sys\main.dol
python tools/rvz_extract.py work\disc\game.rvz work\disc\game.iso
python tools/dol_disasm.py work\disc\main.dol 0x80003140 0x80003200
```

## Build

```powershell
$env:Path = "C:\path\to\ninja;" + $env:Path
cmd /c '"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul && ^
  cmake --build build\moderngekko --target moderngekko-run moderngekko-launcher -j 8'
```

## Generate / compile module

```powershell
build\moderngekko\moderngekko-port.exe build work\game --backend c --toolchain msvc --output build\modules
# then compile the generated module-pgo CMake project with Clang:
# -march=x86-64-v3 -O3 -flto=thin -fprofile-use=... -DDOLRECOMP_C_LOOP_CYCLE_BUDGET=4096 -DDOLRECOMP_C_MAX_CALL_DEPTH=128
```

## Run

```powershell
runner --game work\game --module build\modules\...\gDISCID_recomp.dll `
  --user-dir work\user --core jit --graphics Vulkan --audio Cubeb `
  --load-state work\gameplay.state --automation-dir work\auto --allow-interpreter
```

## Benchmark

```powershell
# low GPU
#   1x, msaa=1, ssaa=false, anisotropy=0, vsync=false
# high GPU
#   shipped settings, vsync=false
# JIT reference
runner ... --core jit
# static
runner ... --core static
```

Read:

```powershell
Get-Content work\auto\status.txt
Get-Content work\user\Logs\ModernGekko.log -Tail 60
```

## Dispatch samples

```powershell
$env:STATICRECOMP_DISPATCH_SAMPLES = "1"
runner ... --automation-dir work\auto
# 20-30 s later
"command=stop" | Set-Content work\auto\commands\stop.txt
```

## PGO

```powershell
llvm-profdata merge -o work\pgo\merged.profdata work\pgo\*.profraw
llvm-profdata show --topn=60 --counts work\pgo\merged.profdata
```

## RecompLauncher

```powershell
python tools\validate_manifest.py docs\recomplauncher.schema.json `
  docs\release\recomplauncher.json
```

Check: manifest at top of zip, start/prepare/config/settings, no game data.

## Icons

```powershell
Add-Type -AssemblyName System.Drawing
$icon = [System.Drawing.Icon]::ExtractAssociatedIcon("SpongeBobRecomp.exe")
$icon.ToBitmap().Save("icon.png", [System.Drawing.Imaging.ImageFormat]::Png)
```

## Release

```powershell
tools\make_release.ps1 -Out dist\MyRecomp-Release
Compress-Archive -Path dist\MyRecomp-Release\* -DestinationPath dist\MyRecomp-vX-Windows-x64.zip
Get-FileHash dist\MyRecomp-vX-Windows-x64.zip -Algorithm SHA256
gh release create vX dist\MyRecomp-vX-Windows-x64.zip dist\SHA256SUMS.txt `
  --title "MyRecomp vX" --notes-file dist\release-notes-vX.md
```

Then download the asset back and verify the hash, schema, files, icons and
absence of game data.

## Agent reminders

- No game data.
- No clean build without asking.
- No generated-code edits.
- No commit/tag/release without approval.
- Measure low/high and static/JIT before optimizing.
- 59.9 FPS = 59.94 Hz = full speed.
