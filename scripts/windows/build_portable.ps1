param(
    [string]$Python = "python",
    [string]$FileSystemRoot = "",
    [switch]$SkipInstall,
    [switch]$NoFrontendBuild,
    [switch]$OneDir
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$ReleaseRoot = Join-Path $Root "release\windows"
$PackageDir = Join-Path $ReleaseRoot "fuxing"
$FinalPackageDir = $PackageDir
$FrontendDist = Join-Path $Root "frontend\dist"
$Wheel = Join-Path $Root "dsetkit-0.3.1-py3-none-any.whl"

function Invoke-Step($Name, [scriptblock]$Block) {
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Block
}

function Copy-RuntimeData($TargetDir) {
    $DataDir = Join-Path $TargetDir "data"
    New-Item -ItemType Directory -Path (Join-Path $DataDir "logs") -Force | Out-Null

    $GroupsFile = Join-Path $Root "data\groups.json"
    if (Test-Path -LiteralPath $GroupsFile) {
        Copy-Item -LiteralPath $GroupsFile -Destination (Join-Path $DataDir "groups.json") -Force
    }

    $TemplatesDir = Join-Path $Root "data\templates"
    if (Test-Path -LiteralPath $TemplatesDir) {
        Copy-Item -LiteralPath $TemplatesDir -Destination (Join-Path $DataDir "templates") -Recurse -Force
    }
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

Invoke-Step "Check dsetkit wheel" {
    if (-not (Test-Path -LiteralPath $Wheel)) {
        throw "Missing wheel: $Wheel"
    }
}

if (-not $SkipInstall) {
    Invoke-Step "Install backend and packaging dependencies" {
        & $Python -m pip install -r (Join-Path $Root "backend\requirements.txt")
        & $Python -m pip install $Wheel
        & $Python -m pip install pyinstaller
    }
}

if (-not $NoFrontendBuild) {
    Invoke-Step "Build frontend" {
        Push-Location (Join-Path $Root "frontend")
        try {
            & npm.cmd install
            & npm.cmd run build
        }
        finally {
            Pop-Location
        }
    }
}

Invoke-Step "Prepare release folders" {
    New-Item -ItemType Directory -Path $ReleaseRoot -Force | Out-Null
    if (Test-Path -LiteralPath (Join-Path $ReleaseRoot "fuxing.exe")) {
        Remove-Item -LiteralPath (Join-Path $ReleaseRoot "fuxing.exe") -Force
    }
    New-Item -ItemType Directory -Path $PackageDir -Force | Out-Null
    Remove-Item -LiteralPath (Join-Path $PackageDir "fuxing.exe") -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $PackageDir "start.bat") -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $PackageDir "fuxing.env") -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $PackageDir "html") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $PackageDir "data") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $PackageDir "dataset") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $PackageDir "datasets") -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path (Join-Path $PackageDir "datasets") -Force | Out-Null
    Copy-RuntimeData $PackageDir
    Write-PortableEnv $PackageDir
    Copy-Item -LiteralPath $FrontendDist -Destination (Join-Path $PackageDir "html") -Recurse
}

Invoke-Step "Build executable" {
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
    if (-not $OneDir) {
        $PyInstallerArgs = @("--onefile") + $PyInstallerArgs
    }
    & $Python -m PyInstaller @PyInstallerArgs

    if ($OneDir) {
        $BuiltDir = Join-Path $ReleaseRoot "fuxing"
        if (-not (Test-Path -LiteralPath (Join-Path $BuiltDir "fuxing.exe"))) {
            throw "PyInstaller did not create expected executable in $BuiltDir"
        }
        Copy-Item -LiteralPath (Join-Path $PackageDir "html") -Destination (Join-Path $BuiltDir "html") -Recurse -Force
        Copy-Item -LiteralPath (Join-Path $PackageDir "data") -Destination (Join-Path $BuiltDir "data") -Recurse -Force
        Copy-Item -LiteralPath (Join-Path $PackageDir "datasets") -Destination (Join-Path $BuiltDir "datasets") -Recurse -Force
        Copy-Item -LiteralPath (Join-Path $PackageDir "fuxing.env") -Destination (Join-Path $BuiltDir "fuxing.env") -Force
        $script:FinalPackageDir = $BuiltDir
    }
    else {
        Move-Item -LiteralPath (Join-Path $ReleaseRoot "fuxing.exe") -Destination (Join-Path $PackageDir "fuxing.exe") -Force
    }
}

Invoke-Step "Write launch helper" {
    $Bat = @"
@echo off
cd /d %~dp0
fuxing.exe
"@
    Set-Content -LiteralPath (Join-Path $FinalPackageDir "start.bat") -Value $Bat -Encoding ASCII
}

Write-Host "Portable Windows package created:" -ForegroundColor Green
Write-Host "  $FinalPackageDir"
Write-Host "Run:"
Write-Host "  $FinalPackageDir\fuxing.exe"
