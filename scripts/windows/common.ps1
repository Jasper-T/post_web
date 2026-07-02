$ErrorActionPreference = "Stop"

$Script:Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$Script:ReleaseRoot = Join-Path $Script:Root "release\windows"
$Script:ProjectName = "web-post"
$Script:PackageDir = Join-Path $Script:ReleaseRoot $Script:ProjectName
$Script:AssetsStageDir = Join-Path $Script:ReleaseRoot "_assets_stage"
$Script:FrontendDist = Join-Path $Script:Root "frontend\dist"
$Script:Wheel = Join-Path $Script:Root "backend/wheels/dsetkit-0.4.1-py3-none-any.whl"
$Script:DemoPipelineDir = Join-Path $Script:Root "data\templates\Ungrouped\demo_image_pipeline"

function Set-ReleaseProjectName([string]$ProjectName = "web-post") {
    $Name = $ProjectName.Trim()
    if (-not $Name) {
        throw "ProjectName cannot be empty."
    }

    $InvalidChars = [System.IO.Path]::GetInvalidFileNameChars()
    if ($Name.IndexOfAny($InvalidChars) -ge 0) {
        throw "ProjectName contains invalid file name characters: $Name"
    }

    $Script:ProjectName = $Name
    $Script:PackageDir = Join-Path $Script:ReleaseRoot $Script:ProjectName
}

function Invoke-Step($Name, [scriptblock]$Block) {
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Block
}

function Resolve-PythonExecutable {
    $VenvPython = Join-Path $Script:Root ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $VenvPython) {
        return $VenvPython
    }

    throw "Python was not found in the uv environment. Run uv sync --group release first."
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
    Copy-Item -LiteralPath (Join-Path $Script:AssetsStageDir "html") -Destination (Join-Path $TargetDir "html") -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $Script:AssetsStageDir "data") -Destination (Join-Path $TargetDir "data") -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $Script:AssetsStageDir "datasets") -Destination (Join-Path $TargetDir "datasets") -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $Script:AssetsStageDir "web-post.env") -Destination (Join-Path $TargetDir "web-post.env") -Force
}

function Copy-RuntimeData($TargetDir) {
    $DataDir = Join-Path $TargetDir "data"
    $TemplateTarget = Join-Path $DataDir "templates\Ungrouped\demo_image_pipeline"

    New-Item -ItemType Directory -Path (Join-Path $DataDir "logs") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $DataDir ".cache") -Force | Out-Null
    New-Item -ItemType Directory -Path (Split-Path -Parent $TemplateTarget) -Force | Out-Null

    Assert-PathExists $Script:DemoPipelineDir "Missing demo pipeline directory: $Script:DemoPipelineDir"

    Copy-Item -LiteralPath $Script:DemoPipelineDir -Destination $TemplateTarget -Recurse -Force
}

function Write-PortableEnv($TargetDir, [string]$FileSystemRoot = "") {
    $EnvPath = Join-Path $TargetDir "web-post.env"
    $Lines = @(
        "# $Script:ProjectName portable runtime configuration",
        "# WEB_POST_FILESYSTEM_ROOT controls the root directory shown by the file browser dialog.",
        "# On Windows, leave it empty to default to the drive that contains $Script:ProjectName.exe.",
        "# Example: WEB_POST_FILESYSTEM_ROOT=D:"
    )
    if ($FileSystemRoot.Trim()) {
        $ResolvedRoot = (Resolve-Path -LiteralPath $FileSystemRoot).Path
        $Lines += "WEB_POST_FILESYSTEM_ROOT=$ResolvedRoot"
    }
    Set-Content -LiteralPath $EnvPath -Value $Lines -Encoding UTF8
}

function Write-LaunchHelper($TargetDir) {
    $ExeName = "$Script:ProjectName.exe"
    $Bat = @"
@echo off
cd /d %~dp0
$ExeName
"@
    Set-Content -LiteralPath (Join-Path $TargetDir "start.bat") -Value $Bat -Encoding ASCII
}

