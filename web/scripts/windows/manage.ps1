$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$ComposeFile = Join-Path $RootDir "docker-compose.yml"

$FrontendService = "webui-frontend"
$BackendService = "webui-backend"

Write-Host "Container status:"
docker compose -f $ComposeFile ps
Write-Host ""

Write-Host "Select service target:"
Write-Host "1) frontend"
Write-Host "2) backend"
Write-Host "3) all"
$ServiceChoice = Read-Host "Enter choice [1-3]"

switch ($ServiceChoice) {
    "1" { $Services = @($FrontendService) }
    "2" { $Services = @($BackendService) }
    "3" { $Services = @($BackendService, $FrontendService) }
    default {
        Write-Error "Invalid service choice: $ServiceChoice"
        exit 1
    }
}

Write-Host ""
Write-Host "Select action:"
Write-Host "1) restart"
Write-Host "2) rebuild"
Write-Host "3) start"
$ActionChoice = Read-Host "Enter choice [1-3]"

switch ($ActionChoice) {
    "1" {
        docker compose -f $ComposeFile restart @Services
    }
    "2" {
        docker compose -f $ComposeFile up -d --build --force-recreate @Services
        docker image prune -f
    }
    "3" {
        docker compose -f $ComposeFile up -d @Services
    }
    default {
        Write-Error "Invalid action choice: $ActionChoice"
        exit 1
    }
}
