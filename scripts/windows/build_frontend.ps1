. "$PSScriptRoot\common.ps1"

Invoke-Step "Build frontend" {
    Push-Location (Join-Path $Script:Root "frontend")
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
