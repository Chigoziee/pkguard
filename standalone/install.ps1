# One-liner install for pkguard standalone binary (no Python required).
#
# Usage:
#   irm https://raw.githubusercontent.com/chigoziee/pkguard/main/standalone/install.ps1 | iex
param(
    [string]$Version = "latest",
    [string]$InstallDir = "$env:LOCALAPPDATA\pkguard"
)

$repo = "chigoziee/pkguard"
$arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "arm64" } else { "amd64" }

if ($Version -eq "latest") {
    $url = "https://github.com/${repo}/releases/latest/download/pkguard-windows-${arch}.exe"
} else {
    $url = "https://github.com/${repo}/releases/download/${Version}/pkguard-windows-${arch}.exe"
}

Write-Host "Downloading pkguard $Version for windows/$arch..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$outPath = Join-Path $InstallDir "pkguard.exe"
Invoke-WebRequest -Uri $url -OutFile $outPath

if ($env:PATH -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$InstallDir", "User")
    $env:Path += ";$InstallDir"
}

Write-Host "Done. pkguard installed to $outPath"
Write-Host "  Run: pkguard --help"