# One-liner install for pkgguard standalone binary (no Python required).
#
# Usage:
#   irm https://raw.githubusercontent.com/chigozie/pkgguard/main/standalone/install.ps1 | iex
param(
    [string]$Version = "latest",
    [string]$InstallDir = "$env:LOCALAPPDATA\pkgguard"
)

$repo = "chigozie/pkgguard"
$arch = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "arm64" } else { "amd64" }

if ($Version -eq "latest") {
    $url = "https://github.com/${repo}/releases/latest/download/pkgguard-windows-${arch}.exe"
} else {
    $url = "https://github.com/${repo}/releases/download/${Version}/pkgguard-windows-${arch}.exe"
}

Write-Host "Downloading pkgguard $Version for windows/$arch..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$outPath = Join-Path $InstallDir "pkgguard.exe"
Invoke-WebRequest -Uri $url -OutFile $outPath

if ($env:PATH -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$InstallDir", "User")
    $env:Path += ";$InstallDir"
}

Write-Host "Done. pkgguard installed to $outPath"
Write-Host "  Run: pkgguard --help"