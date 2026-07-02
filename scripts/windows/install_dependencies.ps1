. "$PSScriptRoot\common.ps1"

Invoke-Step "Sync project dependencies with uv" {
    $UvCommand = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $UvCommand) {
        throw "uv was not found. Install uv first, then rerun release.ps1."
    }

    Push-Location $Script:Root
    try {
        & uv sync --group release
        if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }
    }
    finally {
        Pop-Location
    }

    $PythonExe = Resolve-PythonExecutable
    Invoke-PyInstaller $PythonExe @("--version")
}
