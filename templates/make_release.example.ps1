# Example release packager for a GameCube static recomp.
# Fill in the project paths and run from the project root.
# The real script should live in tools/ and be the only way a release is built.

param(
    [string]$Module = 'H:\Projects\MyRecomp\build\modules\...\module-pgo\gDISCID_recomp.dll',
    [string]$Out = 'H:\Projects\MyRecomp\dist\MyRecomp-Release',
    [string]$AssetName = 'MyRecomp-v0.1.0-Windows-x64'
)

$ErrorActionPreference = 'Stop'
$Root = 'H:\Projects\MyRecomp'

if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
New-Item -ItemType Directory $Out | Out-Null

Copy-Item "$Root\build\moderngekko\MyRecomp.exe" $Out
Copy-Item "$Root\build\moderngekko\MyRecompRunner.exe" $Out
Copy-Item $Module $Out
if (Test-Path "$Root\build\moderngekko\Sys") {
    Copy-Item "$Root\build\moderngekko\Sys" $Out -Recurse
}

New-Item -ItemType Directory "$Out\LICENSES" | Out-Null
Copy-Item "$Root\lib\...\vendor\dolphin\COPYING" "$Out\LICENSES\Dolphin-GPL-2.0.txt"
Copy-Item "$Root\lib\...\DolRecomp\LICENSE" "$Out\LICENSES\DolRecomp.txt"
if (Test-Path "$Root\docs\release\README.txt") { Copy-Item "$Root\docs\release\README.txt" $Out }
if (Test-Path "$Root\docs\release\PLAYERS.md") { Copy-Item "$Root\docs\release\PLAYERS.md" $Out }

$Manifest = "$Root\docs\release\recomplauncher.json"
if (-not (Test-Path $Manifest)) { throw 'REFUSED: recomplauncher.json is missing' }
try { Get-Content $Manifest -Raw | ConvertFrom-Json | Out-Null }
catch { throw "REFUSED: recomplauncher.json is not valid JSON: $_" }
Copy-Item $Manifest $Out

$Forbidden = Get-ChildItem $Out -Recurse -File | Where-Object {
    $_.Name -match '^(main\.dol|boot\.bin|bi2\.bin|fst\.bin|apploader\.img)$' -or
    $_.Extension -match '^\.(iso|rvz|wbfs|gcm|dol|gci|raw)$' -or
    $_.FullName -match '\\Game\\'
}
if ($Forbidden) {
    Write-Output 'REFUSED: game data present:'
    $Forbidden | ForEach-Object { Write-Output "  $($_.FullName)" }
    exit 1
}

$Zip = "$Root\dist\$AssetName.zip"
if (Test-Path $Zip) { Remove-Item $Zip -Force }
Compress-Archive -Path "$Out\*" -DestinationPath $Zip -CompressionLevel Optimal
$Hash = (Get-FileHash $Zip -Algorithm SHA256).Hash
"$Hash  $AssetName.zip" | Set-Content "$Root\dist\SHA256SUMS.txt" -Encoding ascii

Get-Item $Zip | Select-Object FullName, Length, LastWriteTime
Write-Output "sha256=$Hash"
