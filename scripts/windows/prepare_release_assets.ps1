param(
    [string]$FileSystemRoot = "",
    [string]$ProjectName = "web-post"
)

. "$PSScriptRoot\common.ps1"
Set-ReleaseProjectName $ProjectName

Invoke-Step "Prepare release folders and assets" {
    Assert-PathExists $Script:FrontendDist "Missing frontend dist: $Script:FrontendDist. Run build_frontend.ps1 first, or run release.ps1 without -NoFrontendBuild."

    Remove-Item -LiteralPath $Script:PackageDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $Script:AssetsStageDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $Script:ReleaseRoot "$Script:ProjectName.exe") -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $Script:ReleaseRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $Script:AssetsStageDir -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $Script:AssetsStageDir "datasets") -Force | Out-Null

    Copy-RuntimeData $Script:AssetsStageDir
    Write-PortableEnv $Script:AssetsStageDir $FileSystemRoot
    Copy-Item -LiteralPath $Script:FrontendDist -Destination (Join-Path $Script:AssetsStageDir "html") -Recurse -Force
}
