"""
Fetches raw package metadata from npm and PyPI registries.
"""
import requests
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional


NPM_REGISTRY = "https://registry.npmjs.org/{name}"
NPM_DOWNLOADS = "https://api.npmjs.org/downloads/point/last-month/{name}"
PYPI_REGISTRY = "https://pypi.org/pypi/{name}/json"


@dataclass
class PackageMetadata:
    name: str
    ecosystem: str
    exists: bool
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    version_count: int = 0
    maintainer_count: int = 0
    has_repository: bool = False
    has_license: bool = False
    description: str = ""
    weekly_downloads: Optional[int] = None
    latest_version: Optional[str] = None


def _safe_get(url, timeout=8):
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "pkgguard/0.1"})
        return resp
    except requests.RequestException as e:
        return None


def check_npm_package(name: str) -> PackageMetadata:
    resp = _safe_get(NPM_REGISTRY.format(name=name))
    if resp is None:
        return PackageMetadata(name=name, ecosystem="npm", exists=False, error="network_error")
    if resp.status_code == 404:
        return PackageMetadata(name=name, ecosystem="npm", exists=False, error="not_found")
    if resp.status_code != 200:
        return PackageMetadata(name=name, ecosystem="npm", exists=False, error=f"http_{resp.status_code}")

    data = resp.json()
    time_info = data.get("time", {})
    created = time_info.get("created")
    modified = time_info.get("modified")

    versions = data.get("versions", {})
    latest_tag = data.get("dist-tags", {}).get("latest")
    latest = versions.get(latest_tag, {}) if latest_tag else {}

    maintainers = latest.get("maintainers", data.get("maintainers", []))
    repo = latest.get("repository") or data.get("repository")
    license_field = latest.get("license") or data.get("license")

    downloads = None
    dl_resp = _safe_get(NPM_DOWNLOADS.format(name=name))
    if dl_resp is not None and dl_resp.status_code == 200:
        try:
            downloads = dl_resp.json().get("downloads")
        except ValueError:
            pass

    def parse_dt(s):
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None

    return PackageMetadata(
        name=name,
        ecosystem="npm",
        exists=True,
        created_at=parse_dt(created),
        last_updated=parse_dt(modified),
        version_count=len(versions),
        maintainer_count=len(maintainers) if isinstance(maintainers, list) else 0,
        has_repository=bool(repo),
        has_license=bool(license_field),
        description=data.get("description", "") or "",
        weekly_downloads=downloads,
        latest_version=latest_tag,
    )


def check_pypi_package(name: str) -> PackageMetadata:
    resp = _safe_get(PYPI_REGISTRY.format(name=name))
    if resp is None:
        return PackageMetadata(name=name, ecosystem="pypi", exists=False, error="network_error")
    if resp.status_code == 404:
        return PackageMetadata(name=name, ecosystem="pypi", exists=False, error="not_found")
    if resp.status_code != 200:
        return PackageMetadata(name=name, ecosystem="pypi", exists=False, error=f"http_{resp.status_code}")

    data = resp.json()
    info = data.get("info", {})
    releases = data.get("releases", {})

    # earliest upload time across all releases = creation date proxy
    all_upload_times = []
    last_upload = None
    for version, files in releases.items():
        for f in files:
            t = f.get("upload_time_iso_8601")
            if t:
                all_upload_times.append(t)

    def parse_dt(s):
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None

    parsed_times = sorted(filter(None, (parse_dt(t) for t in all_upload_times)))
    created_at = parsed_times[0] if parsed_times else None
    last_updated = parsed_times[-1] if parsed_times else None

    project_urls = info.get("project_urls") or {}
    has_repo = any(
        "github.com" in (v or "").lower() or "gitlab.com" in (v or "").lower() or "repo" in k.lower()
        for k, v in project_urls.items()
    ) or bool(info.get("home_page") and ("github.com" in info["home_page"].lower()))

    license_field = info.get("license")

    return PackageMetadata(
        name=name,
        ecosystem="pypi",
        exists=True,
        created_at=created_at,
        last_updated=last_updated,
        version_count=len(releases),
        maintainer_count=1 if (info.get("author") or info.get("maintainer")
                                or info.get("author_email") or info.get("maintainer_email")) else 0,
        has_repository=has_repo,
        has_license=bool(license_field and license_field.strip()),
        description=info.get("summary", "") or "",
        weekly_downloads=None,  # PyPI has no free official downloads API; left as None
        latest_version=info.get("version"),
    )


def check_package(name: str, ecosystem: str) -> PackageMetadata:
    if ecosystem == "npm":
        return check_npm_package(name)
    elif ecosystem == "pypi":
        return check_pypi_package(name)
    else:
        raise ValueError(f"Unknown ecosystem: {ecosystem}")
