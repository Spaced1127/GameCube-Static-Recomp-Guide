# Example PGO workflow for a DolRecomp C module.
# Fill in the paths and run from the project root.
# This is a template, not a one-click build for every template layout.

$ErrorActionPreference = 'Stop'

$ProjectRoot = 'H:\Projects\MyRecomp'
$BuildDir    = "$ProjectRoot\build\moderngekko"
$GameRoot    = "$ProjectRoot\work\game"
$UserDir     = "$ProjectRoot\work\pgo-user"
$State       = "$ProjectRoot\work\gameplay.state"
$PgoDir      = "$ProjectRoot\work\pgo"
$ModuleRoot  = "$ProjectRoot\build\modules"
$Clang       = 'C:\Program Files\LLVM\bin\clang.exe'
$LlvmProfdata= 'C:\Program Files\LLVM\bin\llvm-profdata.exe'

New-Item -ItemType Directory $PgoDir -Force | Out-Null

# 1. Generate the C into build/modules/<ID>/...
# & "$BuildDir\moderngekko-port.exe" build $GameRoot --backend c --toolchain msvc --output $ModuleRoot

# 2. Instrumented build. The generated module project is produced by the port tool;
#    point CMake at its module-pgogen source or add -fprofile-generate to its flags.
# cmake -S <pgogen-source> -B <pgogen-build> -G Ninja `
#   -DCMAKE_C_COMPILER="$Clang" `
#   -DCMAKE_C_FLAGS="-march=x86-64-v3 -mtune=generic -O3 -DNDEBUG -std=gnu11 -flto=thin -fprofile-generate=$PgoDir"
# cmake --build <pgogen-build> -j 8

# 3. Run representative gameplay with the instrumented module.
#    The profile flushes on a graceful stop, so use the automation stop command.
$env:LLVM_PROFILE_FILE = "$PgoDir\play-%p.profraw"
# & "$BuildDir\MyRecompRunner.exe" --game $GameRoot `
#   --module <pgogen-build>\gDISCID_recomp.dll `
#   --user-dir $UserDir --load-state $State `
#   --graphics Vulkan --audio Null --allow-interpreter `
#   --automation-dir "$ProjectRoot\work\auto-pgo"
# Start-Sleep -Seconds 30
# 'command=stop' | Set-Content "$ProjectRoot\work\auto-pgo\commands\stop.txt"

# 4. Merge.
& $LlvmProfdata merge -o "$PgoDir\merged.profdata" (Get-ChildItem "$PgoDir\*.profraw").FullName

# 5. Profile-use build.
# cmake -S <pgo-source> -B <pgo-build> -G Ninja `
#   -DCMAKE_C_COMPILER="$Clang" `
#   -DCMAKE_C_FLAGS="-march=x86-64-v3 -mtune=generic -O3 -DNDEBUG -std=gnu11 -flto=thin -fprofile-use=$PgoDir\merged.profdata -Wno-profile-instr-out-of-date -Wno-profile-instr-unprofiled"
# cmake --build <pgo-build> -j 8

# 6. Inspect the hot functions.
& $LlvmProfdata show --topn=60 --counts "$PgoDir\merged.profdata"

Write-Host "PGO merged. Rebuild with -fprofile-use and benchmark the same state."
