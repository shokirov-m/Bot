# Создаёт junction tower_bot/assets -> content/assets (Windows).
$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$link = Join-Path $root "assets"
$target = Join-Path $root "content\assets"
if (Test-Path $link) {
    Write-Host "Already exists: $link"
    exit 0
}
cmd /c mklink /J "`"$link`"" "`"$target`""
Write-Host "Created junction: assets -> content/assets"
