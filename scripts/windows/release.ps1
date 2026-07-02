param(
    [string]$ProjectName = "web-post",
    [string]$FileSystemRoot = "",
    [switch]$NoFrontendBuild,
    [switch]$OneDir,
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"

. "$PSScriptRoot\common.ps1"
Set-ReleaseProjectName $ProjectName

if ($OneDir -and $OneFile) {
    throw "Use only one of -OneDir or -OneFile. By default this script builds OneDir."
}

$UseOneFile = [bool]$OneFile

Invoke-Step "Check release inputs" {
    Assert-PathExists $Script:Wheel "Missing wheel: $Script:Wheel"
    Assert-PathExists $Script:DemoPipelineDir "Missing demo pipeline directory: $Script:DemoPipelineDir"

    Write-Host "Project: $Script:ProjectName"
    Write-Host "Mode: $(if ($UseOneFile) { 'onefile' } else { 'onedir' })"
    Write-Host "Dependency sync: uv sync --group release"
    Write-Host "Python: .venv\Scripts\python.exe after uv sync"
}

function Invoke-Phase {
    param(
        [string]$ScriptName,
        [hashtable]$NamedArgs = @{}
    )

    $ScriptPath = Join-Path $PSScriptRoot $ScriptName

    if (-not (Test-Path -LiteralPath $ScriptPath)) {
        throw "Missing script: $ScriptPath"
    }

    $ArgText = if ($NamedArgs.Count -gt 0) {
        ($NamedArgs.GetEnumerator() | ForEach-Object {
            if ($_.Value -is [bool]) {
                if ($_.Value) {
                    "-$($_.Key)"
                }
            } else {
                "-$($_.Key) `"$($_.Value)`""
            }
        }) -join " "
    } else {
        ""
    }

    Write-Host "Run: $ScriptPath $ArgText" -ForegroundColor DarkGray

    $PreviousExitCode = $global:LASTEXITCODE
    $global:LASTEXITCODE = 0
    try {
        & $ScriptPath @NamedArgs
        if (-not $?) {
            throw "Script failed: $ScriptPath"
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Script failed with exit code $LASTEXITCODE : $ScriptPath"
        }
    }
    finally {
        if ($LASTEXITCODE -eq 0) {
            $global:LASTEXITCODE = $PreviousExitCode
        }
    }
}

Invoke-Phase -ScriptName "install_dependencies.ps1"

if (-not $NoFrontendBuild) {
    Invoke-Phase -ScriptName "build_frontend.ps1"
}

$PrepareArgs = @{ ProjectName = $Script:ProjectName }

if ($FileSystemRoot.Trim()) {
    $PrepareArgs["FileSystemRoot"] = $FileSystemRoot
}

Invoke-Phase -ScriptName "prepare_release_assets.ps1" -NamedArgs $PrepareArgs

$BackendArgs = @{ ProjectName = $Script:ProjectName }

if ($UseOneFile) {
    $BackendArgs["OneFile"] = $true
}

Invoke-Phase -ScriptName "build_backend_executable.ps1" -NamedArgs $BackendArgs

$AssembleArgs = @{ ProjectName = $Script:ProjectName }

if ($UseOneFile) {
    $AssembleArgs["OneFile"] = $true
}

Invoke-Phase -ScriptName "assemble_portable.ps1" -NamedArgs $AssembleArgs
