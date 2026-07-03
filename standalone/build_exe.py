"""
Build standalone pkguard binaries with PyInstaller (no Python required to run).

Prerequisites:
    pip install pyinstaller

Usage:
    python build_exe.py              # build for current platform
    python build_exe.py --onefile    # single-file binary

Output lands in ./dist/
"""
import subprocess
import sys
import platform


def main():
    onefile = "--onefile" in sys.argv

    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", "pkguard",
        "--console",
        "--clean",
        "--noconfirm",
    ]

    if onefile:
        args.append("--onefile")
    else:
        args.append("--onedir")

    args.extend([
        "--hidden-import", "requests",
        "--hidden-import", "concurrent.futures",
    ])

    args.append("pkguard.py")

    print(f"Building for {platform.system()} ({platform.machine()})...")
    subprocess.run(args, check=True)

    print("\nDone. Binary is in ./dist/")


if __name__ == "__main__":
    main()