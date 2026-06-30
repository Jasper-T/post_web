param(
    [string]$Python = "",
    [string]$FileSystemRoot = "",
    [switch]$SkipInstall,
    [switch]$NoFrontendBuild,
    [switch]$OneDir,
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$ReleaseRoot = Join-Path $Root "release\windows"
$PackageDir = Join-Path $ReleaseRoot "fuxing"
$AssetsStageDir = Join-Path $ReleaseRoot "_assets_stage"
$FrontendDist = Join-Path $Root "frontend\dist"
$Wheel = Join-Path $Root "dsetkit-0.4.0-py3-none-any.whl"
$DemoPipelineDir = Join-Path $Root "data\templates\Ungrouped\demo_image_pipeline"
$GroupsFile = Join-Path $Root "data\groups.json"
$FinalPackageDir = $PackageDir

function Invoke-Step($Name, [scriptblock]$Block) {
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Block
}

function Resolve-PythonExecutable {
    if ($Python.Trim()) {
        return (Resolve-Path -LiteralPath $Python).Path
    }

    $VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $VenvPython) {
        return $VenvPython
    }

    $Command = Get-Command python -ErrorAction SilentlyContinue
    if ($Command) {
        return $Command.Source
    }

    throw "Python was not found. Create .venv first or pass -Python <path-to-python.exe>."
}

function Assert-PathExists($Path, $Message) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw $Message
    }
}
function Invoke-PythonPackageInstall($PythonPath, [string[]]$InstallArgs, $FailureMessage) {
    $UvCommand = Get-Command uv -ErrorAction SilentlyContinue
    if ($UvCommand) {
        & uv pip install --python $PythonPath @InstallArgs
        if ($LASTEXITCODE -eq 0) {
            return
        }
    }

    & $PythonPath -m pip install @InstallArgs
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

function Invoke-PyInstaller($PythonPath, [string[]]$PyInstallerArgs) {
    & $PythonPath -m PyInstaller @PyInstallerArgs
    if ($LASTEXITCODE -eq 0) {
        return
    }

    & $PythonPath -m pyinstaller @PyInstallerArgs
    if ($LASTEXITCODE -eq 0) {
        return
    }

    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

function Copy-ReleaseAssets($TargetDir) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $AssetsStageDir "html") -Destination (Join-Path $TargetDir "html") -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $AssetsStageDir "data") -Destination (Join-Path $TargetDir "data") -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $AssetsStageDir "datasets") -Destination (Join-Path $TargetDir "datasets") -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $AssetsStageDir "fuxing.env") -Destination (Join-Path $TargetDir "fuxing.env") -Force
}

function Copy-RuntimeData($TargetDir) {
    $DataDir = Join-Path $TargetDir "data"
    $TemplateTarget = Join-Path $DataDir "templates\Ungrouped\demo_image_pipeline"

    New-Item -ItemType Directory -Path (Join-Path $DataDir "logs") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $DataDir "results") -Force | Out-Null
    New-Item -ItemType Directory -Path (Split-Path -Parent $TemplateTarget) -Force | Out-Null

    Assert-PathExists $GroupsFile "Missing groups file: $GroupsFile"
    Assert-PathExists $DemoPipelineDir "Missing demo pipeline directory: $DemoPipelineDir"

    Copy-Item -LiteralPath $GroupsFile -Destination (Join-Path $DataDir "groups.json") -Force
    Copy-Item -LiteralPath $DemoPipelineDir -Destination $TemplateTarget -Recurse -Force
}

function Write-PortableEnv($TargetDir) {
    $EnvPath = Join-Path $TargetDir "fuxing.env"
    $Lines = @(
        "# Fuxing portable runtime configuration",
        "# FUXING_FILESYSTEM_ROOT controls the root directory shown by the file browser dialog.",
        "# On Windows, leave it empty to default to the drive that contains fuxing.exe.",
        "# Example: FUXING_FILESYSTEM_ROOT=D:\"
    )
    if ($FileSystemRoot.Trim()) {
        $ResolvedRoot = (Resolve-Path -LiteralPath $FileSystemRoot).Path
        $Lines += "FUXING_FILESYSTEM_ROOT=$ResolvedRoot"
    }
    Set-Content -LiteralPath $EnvPath -Value $Lines -Encoding UTF8
}

function Write-LaunchHelper($TargetDir) {
    $Bat = @"
@echo off
cd /d %~dp0
fuxing.exe
"@
    Set-Content -LiteralPath (Join-Path $TargetDir "start.bat") -Value $Bat -Encoding ASCII
}

if ($OneDir -and $OneFile) {
    throw "Use only one of -OneDir or -OneFile. By default this script builds OneDir."
}

$UseOneFile = [bool]$OneFile
$PythonExe = Resolve-PythonExecutable

Invoke-Step "Check release inputs" {
    Assert-PathExists $Wheel "Missing wheel: $Wheel"
    Assert-PathExists $DemoPipelineDir "Missing demo pipeline directory: $DemoPipelineDir"
    Write-Host "Python: $PythonExe"
    Write-Host "Mode: $(if ($UseOneFile) { 'onefile' } else { 'onedir' })"
}

if (-not $SkipInstall) {
    Invoke-Step "Install backend and packaging dependencies" {
        Invoke-PythonPackageInstall $PythonExe @("-r", (Join-Path $Root "backend\requirements.txt")) "Failed to install backend requirements"
        Invoke-PythonPackageInstall $PythonExe @($Wheel) "Failed to install dsetkit wheel"
        Invoke-PythonPackageInstall $PythonExe @("pyinstaller") "Failed to install pyinstaller"
        Invoke-PyInstaller $PythonExe @("--version")
    }
}

if (-not $NoFrontendBuild) {
    Invoke-Step "Build frontend" {
        Push-Location (Join-Path $Root "frontend")
        try {
            & npm.cmd install
            if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
            & npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
        }
        finally {
            Pop-Location
        }
    }
}

Invoke-Step "Prepare release folders and assets" {
    Assert-PathExists $FrontendDist "Missing frontend dist: $FrontendDist. Run without -NoFrontendBuild first."

    Remove-Item -LiteralPath $PackageDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $AssetsStageDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $ReleaseRoot "fuxing.exe") -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $ReleaseRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $AssetsStageDir -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $AssetsStageDir "datasets") -Force | Out-Null

    Copy-RuntimeData $AssetsStageDir
    Write-PortableEnv $AssetsStageDir
    Copy-Item -LiteralPath $FrontendDist -Destination (Join-Path $AssetsStageDir "html") -Recurse -Force
}

Invoke-Step "Build backend executable" {
    $PyInstallerArgs = @(
        "--clean",
        "--noconfirm",
        "--name", "fuxing",
        "--paths", $Root,
        "--collect-all", "dsetkit",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "requests",
        "--hidden-import", "tqdm",
        "--distpath", $ReleaseRoot,
        "--workpath", (Join-Path $Root "build\pyinstaller"),
        "--specpath", (Join-Path $Root "build\pyinstaller"),
        (Join-Path $Root "backend\launcher.py")
    )

    if ($UseOneFile) {
        $PyInstallerArgs = @("--onefile") + $PyInstallerArgs
    }

    Invoke-PyInstaller $PythonExe $PyInstallerArgs
}

Invoke-Step "Assemble portable package" {
    if ($UseOneFile) {
        $BuiltExe = Join-Path $ReleaseRoot "fuxing.exe"
        if (-not (Test-Path -LiteralPath $BuiltExe)) {
            $CandidateExe = Get-ChildItem -LiteralPath $ReleaseRoot -Recurse -Filter "fuxing.exe" -File -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($CandidateExe) {
                $BuiltExe = $CandidateExe.FullName
            }
            else {
                throw "PyInstaller finished but fuxing.exe was not found under $ReleaseRoot. Check Windows Security quarantine, or run default OneDir mode."
            }
        }
        New-Item -ItemType Directory -Path $PackageDir -Force | Out-Null
        Copy-ReleaseAssets $PackageDir
        Move-Item -LiteralPath $BuiltExe -Destination (Join-Path $PackageDir "fuxing.exe") -Force
        $script:FinalPackageDir = $PackageDir
    }
    else {
        $BuiltDir = Join-Path $ReleaseRoot "fuxing"
        $BuiltExe = Join-Path $BuiltDir "fuxing.exe"
        if (-not (Test-Path -LiteralPath $BuiltExe)) {
            throw "PyInstaller did not create expected executable: $BuiltExe"
        }
        Copy-ReleaseAssets $BuiltDir
        $script:FinalPackageDir = $BuiltDir
    }

    Write-LaunchHelper $script:FinalPackageDir
}

Invoke-Step "Clean temporary release assets" {
    Remove-Item -LiteralPath $AssetsStageDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Portable Windows package created:" -ForegroundColor Green
Write-Host "  $FinalPackageDir"
Write-Host "Run:"
Write-Host "  $FinalPackageDir\fuxing.exe"