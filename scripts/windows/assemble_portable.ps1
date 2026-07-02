param(
    [string]$ProjectName = "web-post",
    [switch]$OneFile
)

. "$PSScriptRoot\common.ps1"
Set-ReleaseProjectName $ProjectName

$FinalPackageDir = $Script:PackageDir
$ExeName = "$Script:ProjectName.exe"

Invoke-Step "Assemble portable package" {
    Assert-PathExists $Script:AssetsStageDir "Missing staged assets: $Script:AssetsStageDir. Run prepare_release_assets.ps1 first."

    if ($OneFile) {
        $BuiltExe = Join-Path $Script:ReleaseRoot $ExeName
        if (-not (Test-Path -LiteralPath $BuiltExe)) {
            $CandidateExe = Get-ChildItem -LiteralPath $Script:ReleaseRoot -Recurse -Filter $ExeName -File -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($CandidateExe) {
                $BuiltExe = $CandidateExe.FullName
            }
            else {
                throw "PyInstaller finished but $ExeName was not found under $Script:ReleaseRoot. Check Windows Security quarantine, or run default OneDir mode."
            }
        }
        New-Item -ItemType Directory -Path $Script:PackageDir -Force | Out-Null
        Copy-ReleaseAssets $Script:PackageDir
        Move-Item -LiteralPath $BuiltExe -Destination (Join-Path $Script:PackageDir $ExeName) -Force
        $FinalPackageDir = $Script:PackageDir
    }
    else {
        $BuiltDir = Join-Path $Script:ReleaseRoot $Script:ProjectName
        $BuiltExe = Join-Path $BuiltDir $ExeName
        if (-not (Test-Path -LiteralPath $BuiltExe)) {
            throw "PyInstaller did not create expected executable: $BuiltExe"
        }
        Copy-ReleaseAssets $BuiltDir
        $FinalPackageDir = $BuiltDir
    }

    Write-LaunchHelper $FinalPackageDir
    Get-ChildItem -LiteralPath $FinalPackageDir -Recurse -Filter "direct_url.json" -File -ErrorAction SilentlyContinue | Remove-Item -Force
}

Invoke-Step "Clean temporary release assets" {
    Remove-Item -LiteralPath $Script:AssetsStageDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Portable Windows package created:" -ForegroundColor Green
Write-Host "  $FinalPackageDir"
Write-Host "Run:"
Write-Host "  $(Join-Path $FinalPackageDir $ExeName)"

