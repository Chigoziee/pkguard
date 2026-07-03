#!/usr/bin/env bash
# One-liner install for pkguard (standalone binary, no Python required).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/chigoziee/pkguard/main/standalone/install.sh | bash
set -euo pipefail

REPO="chigoziee/pkguard"
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
    DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/pkguard-${OS}-${ARCH}"
else
    DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/pkguard-${OS}-${ARCH}"
fi

echo "Downloading pkguard ${VERSION} for ${OS}/${ARCH}..."
curl -fsSL "$DOWNLOAD_URL" -o "${BIN_DIR}/pkguard"
chmod +x "${BIN_DIR}/pkguard"

echo "Done. pkguard installed to ${BIN_DIR}/pkguard"
echo "  Run: pkguard --help"