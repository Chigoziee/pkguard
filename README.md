# pkgguard

Validate npm and PyPI packages **before** you install them — catches
[slopsquatting](https://en.wikipedia.org/wiki/Slopsquatting) (malicious packages
registered under names that AI coding assistants commonly hallucinate), typosquats,
and generally low-trust/newly-published packages.

## Install

### Python users (pip)

```bash
pip install pkgguard
```

### npm / Node.js users (standalone binary, no Python required)

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/chigozie/pkgguard/main/standalone/install.ps1 | iex
```

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/chigozie/pkgguard/main/standalone/install.sh | bash
```

Or download the pre-built binary directly from [GitHub Releases](https://github.com/chigozie/pkgguard/releases).

### From source

```bash
git clone https://github.com/chigozie/pkgguard.git
cd pkgguard
pip install -e .
```

## Usage

### 1. Check specific packages

```bash
pkgguard check requests flask reqeusts --ecosystem pypi
pkgguard check react react-dom reactt --ecosystem npm
```

### 2. Scan a manifest file

```bash
pkgguard scan requirements.txt
pkgguard scan package.json
```

### 3. Wrap an install command (blocks risky installs automatically)

```bash
pkgguard install pip install some-package another-package
pkgguard install npm install some-package another-package

# override and install anyway:
pkgguard install pip install some-package --force
```

Exits with code `1` if anything is flagged as risky or missing — safe to drop into
a CI step or a pre-commit/pre-push git hook.

## What it checks

| Check | Why it matters |
|---|---|
| **Existence** | The core slopsquatting check — does this package actually exist? |
| **Typosquat distance** | Is the name suspiciously close (edit distance ≤2) to a well-known package? |
| **Age** | Brand-new packages (<30 days) have had little time for community scrutiny |
| **Version count** | A single published version means no track record |
| **Maintainer info** | Missing maintainer/author metadata is a red flag |
| **Repository link** | No linked source repo = can't inspect the code |
| **License** | Missing license is a minor signal, often correlates with low-effort/malicious packages |
| **Download counts** (npm only) | Very low real-world usage despite being "well-known" to an AI is suspicious |

Each check contributes to a 0–100 risk score. Anything ≥35 is flagged as risky by
the `install` wrapper.

## Suggested workflow integration

- **Local dev**: alias `pip install` / `npm install` to `pkgguard install pip install` /
  `pkgguard install npm install` in your shell profile.
- **CI**: add `pkgguard scan requirements.txt` (or `package.json`) as a pipeline step
  before dependency installation; non-zero exit fails the build.
- **Pre-commit hook**: run `pkgguard scan` against manifest files that changed in the
  commit.

## Building the standalone binary

```bash
cd standalone
pip install pyinstaller
python build_exe.py --onefile
```

Outputs to `standalone/dist/`. Cross-platform builds require running on each target OS.

## Limitations

- The "popular packages" typosquat reference list is a curated sample (~80-100
  per ecosystem), not exhaustive — extend `pkgguard/popular.py` with packages
  relevant to your org for better coverage.
- PyPI has no free official downloads API, so download-count scoring only applies
  to npm currently (pypistats.org could be integrated as a future enhancement).
- Heuristic scores are signals, not proof — always use judgment, especially for
  medium-risk results.