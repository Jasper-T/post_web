param(
    [string]$ProjectName = "web-post",
    [switch]$OneFile
)

. "$PSScriptRoot\common.ps1"
Set-ReleaseProjectName $ProjectName

$PythonExe = Resolve-PythonExecutable

Invoke-Step "Build backend executable" {
    $PyInstallerArgs = @(
        "--clean",
        "--noconfirm",
        "--name", $Script:ProjectName,
        "--paths", $Script:Root,
        "--collect-all", "dsetkit",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "requests",
        "--hidden-import", "tqdm",
        "--distpath", $Script:ReleaseRoot,
        "--workpath", (Join-Path $Script:Root "build\pyinstaller"),
        "--specpath", (Join-Path $Script:Root "build\pyinstaller"),
        (Join-Path $Script:Root "backend\launcher.py")
    )

    if ($OneFile) {
        $PyInstallerArgs = @("--onefile") + $PyInstallerArgs
    }

    Invoke-PyInstaller $PythonExe $PyInstallerArgs
}
