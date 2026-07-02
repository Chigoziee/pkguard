#!/usr/bin/env bash
# One-liner install for pkgguard (standalone binary, no Python required).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/chigozie/pkgguard/main/standalone/install.sh | bash
set -euo pipefail

REPO="chigozie/pkgguard"
VERSION="${PKGGUARD_VERSION:-latest}"
BIN_DIR="${PKGGUARD_INSTALL_DIR:-/usr/local/bin}"

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$OS" in
    linux)   OS="linux" ;;
    darwin)  OS="macos" ;;
    *)       echo "Unsupported OS: $OS"; exit 1 ;;
esac

case "$ARCH" in
    x86_64|amd64) ARCH="amd64" ;;
    arm64|aarch64) ARCH="arm64" ;;
    *)             echo "Unsupported arch: $ARCH"; exit 1 ;;
esac

if [ "$VERSION" = "latest" ]; then
    DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/pkgguard-${OS}-${ARCH}"
else
    DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/pkgguard-${OS}-${ARCH}"
fi

echo "Downloading pkgguard ${VERSION} for ${OS}/${ARCH}..."
curl -fsSL "$DOWNLOAD_URL" -o "${BIN_DIR}/pkgguard"
chmod +x "${BIN_DIR}/pkgguard"

echo "Done. pkgguard installed to ${BIN_DIR}/pkgguard"
echo "  Run: pkgguard --help"