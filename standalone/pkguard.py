#!/usr/bin/env python3
"""
pkguard — validate npm / PyPI packages before you install them.

Usage:
    pkguard check requests flask left-pad --ecosystem pypi
    pkguard check react react-dom is-even --ecosystem npm
    pkguard scan requirements.txt
    pkguard scan package.json
    pkguard install npm install some-package another-package
    pkguard install pip install some-package another-package
"""
import argparse
import json
import re
import subprocess
import sys
import concurrent.futures as cf

import requests
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Optional

POPULAR_NPM = {
    "react", "react-dom", "vue", "angular", "express", "lodash", "axios", "moment",
    "webpack", "babel", "typescript", "eslint", "jest", "mocha", "chalk", "commander",
    "chalk", "dotenv", "next", "nuxt", "svelte", "redux", "vuex", "jquery", "underscore",
    "request", "async", "bluebird", "rxjs", "socket.io", "prisma", "sequelize", "mongoose",
    "passport", "bcrypt", "jsonwebtoken", "uuid", "nodemon", "pm2", "cors", "helmet",
    "body-parser", "cookie-parser", "multer", "nodemailer", "puppeteer", "playwright",
    "cheerio", "yargs", "inquirer", "ora", "figlet", "colors", "chokidar", "glob",
    "rimraf", "fs-extra", "cross-env", "concurrently", "husky", "lint-staged",
    "prettier", "styled-components", "classnames", "prop-types", "immer", "zustand",
    "recoil", "formik", "yup", "zod", "graphql", "apollo-client", "date-fns", "dayjs",
    "vite", "rollup", "parcel", "esbuild", "tailwindcss", "postcss", "sass", "less",
}

POPULAR_PYPI = {
    "numpy", "pandas", "requests", "flask", "django", "scipy", "matplotlib", "scikit-learn",
    "tensorflow", "torch", "pytorch", "keras", "pillow", "pytest", "setuptools", "pip",
    "wheel", "boto3", "botocore", "sqlalchemy", "click", "jinja2", "pyyaml", "cryptography",
    "certifi", "urllib3", "idna", "charset-normalizer", "six", "python-dateutil", "attrs",
    "packaging", "colorama", "typing-extensions", "aiohttp", "gunicorn", "celery", "redis",
    "psycopg2", "pymongo", "fastapi", "uvicorn", "pydantic", "starlette", "httpx", "beautifulsoup4",
    "lxml", "selenium", "scrapy", "openpyxl", "xlrd", "tqdm", "rich", "loguru", "black",
    "flake8", "mypy", "isort", "poetry", "virtualenv", "pipenv", "docker", "kubernetes",
    "paramiko", "fabric", "invoke", "pyjwt", "bcrypt", "passlib", "cffi", "protobuf",
    "grpcio", "pyarrow", "dask", "xgboost", "lightgbm", "nltk", "spacy", "gensim",
    "opencv-python", "imageio", "networkx", "sympy", "statsmodels", "plotly", "seaborn",
    "bokeh", "streamlit", "gradio", "openai", "anthropic", "langchain", "transformers",
}


def get_popular_set(ecosystem: str) -> set:
    return POPULAR_NPM if ecosystem == "npm" else POPULAR_PYPI


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
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "pkguard/0.1"})
        return resp
    except requests.RequestException:
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

    all_upload_times = []
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
        weekly_downloads=None,
        latest_version=info.get("version"),
    )


def check_package(name: str, ecosystem: str) -> PackageMetadata:
    if ecosystem == "npm":
        return check_npm_package(name)
    elif ecosystem == "pypi":
        return check_pypi_package(name)
    else:
        raise ValueError(f"Unknown ecosystem: {ecosystem}")


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[-1]


@dataclass
class RiskFinding:
    severity: str
    reason: str


@dataclass
class RiskReport:
    package: str
    ecosystem: str
    exists: bool
    findings: List[RiskFinding] = field(default_factory=list)
    risk_score: int = 0

    @property
    def risk_label(self) -> str:
        if not self.exists:
            return "DOES NOT EXIST"
        if self.risk_score >= 70:
            return "HIGH RISK"
        if self.risk_score >= 35:
            return "MEDIUM RISK"
        if self.risk_score >= 15:
            return "LOW RISK"
        return "LOOKS OK"


def _closest_popular_match(name: str, ecosystem: str):
    popular = get_popular_set(ecosystem)
    if name.lower() in popular:
        return None, None
    best_name, best_dist = None, 999
    for p in popular:
        d = levenshtein(name.lower(), p.lower())
        if d < best_dist:
            best_dist = d
            best_name = p
    return best_name, best_dist


def evaluate(meta: PackageMetadata) -> RiskReport:
    report = RiskReport(package=meta.name, ecosystem=meta.ecosystem, exists=meta.exists)

    if not meta.exists:
        if meta.error == "not_found":
            report.findings.append(RiskFinding(
                "critical",
                "Package does not exist on the registry. If an AI assistant suggested "
                "this, it is very likely a hallucinated package name. DO NOT install "
                "unless you can otherwise verify it's legitimate."
            ))
        else:
            report.findings.append(RiskFinding(
                "info", f"Could not verify package (reason: {meta.error}). Try again or check manually."
            ))
        report.risk_score = 100 if meta.error == "not_found" else 0
        return report

    score = 0

    closest, dist = _closest_popular_match(meta.name, meta.ecosystem)
    if closest is not None and dist <= 2 and meta.name.lower() != closest.lower():
        report.findings.append(RiskFinding(
            "critical",
            f"Name is suspiciously close to popular package '{closest}' "
            f"(edit distance {dist}). Possible typosquat."
        ))
        score += 40

    if meta.created_at:
        age_days = (datetime.now(timezone.utc) - meta.created_at).days
        if age_days < 7:
            report.findings.append(RiskFinding("high", f"Package is brand new ({age_days} day(s) old)."))
            score += 25
        elif age_days < 30:
            report.findings.append(RiskFinding("medium", f"Package is very young ({age_days} days old)."))
            score += 15
        elif age_days < 90:
            report.findings.append(RiskFinding("low", f"Package is relatively young ({age_days} days old)."))
            score += 5
    else:
        report.findings.append(RiskFinding("info", "Could not determine package age."))

    if meta.version_count <= 1:
        report.findings.append(RiskFinding("medium", "Only one published version — little history to evaluate."))
        score += 10

    if meta.maintainer_count == 0:
        report.findings.append(RiskFinding("medium", "No identifiable maintainer information."))
        score += 10
    elif meta.maintainer_count == 1:
        report.findings.append(RiskFinding("low", "Single maintainer (not necessarily bad, but higher single-point risk)."))
        score += 3

    if not meta.has_repository:
        report.findings.append(RiskFinding("medium", "No linked source repository."))
        score += 10
    if not meta.has_license:
        report.findings.append(RiskFinding("low", "No license declared."))
        score += 5

    if not meta.description or len(meta.description.strip()) < 10:
        report.findings.append(RiskFinding("low", "Missing or very sparse package description."))
        score += 5

    if meta.ecosystem == "npm" and meta.weekly_downloads is not None:
        if meta.weekly_downloads < 10:
            report.findings.append(RiskFinding("high", f"Extremely low weekly downloads ({meta.weekly_downloads})."))
            score += 20
        elif meta.weekly_downloads < 500:
            report.findings.append(RiskFinding("medium", f"Low weekly downloads ({meta.weekly_downloads})."))
            score += 8

    if not report.findings:
        report.findings.append(RiskFinding("info", "No red flags found. Still exercise normal diligence."))

    report.risk_score = min(score, 100)
    return report


SEVERITY_COLOR = {
    "critical": "\033[91m",
    "high": "\033[91m",
    "medium": "\033[93m",
    "low": "\033[94m",
    "info": "\033[90m",
}
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"

LABEL_COLOR = {
    "DOES NOT EXIST": "\033[91m",
    "HIGH RISK": "\033[91m",
    "MEDIUM RISK": "\033[93m",
    "LOW RISK": "\033[94m",
    "LOOKS OK": "\033[92m",
}


def print_report(report: RiskReport):
    color = LABEL_COLOR.get(report.risk_label, "")
    print(f"{BOLD}{report.package}{RESET} ({report.ecosystem})  "
          f"{color}[{report.risk_label}]{RESET}  score={report.risk_score}/100")
    for f in report.findings:
        c = SEVERITY_COLOR.get(f.severity, "")
        print(f"    {c}[{f.severity.upper()}]{RESET} {f.reason}")
    print()


def run_check(names, ecosystem):
    reports = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(check_package, n, ecosystem): n for n in names}
        results = {}
        for fut in cf.as_completed(futures):
            n = futures[fut]
            try:
                meta = fut.result()
            except Exception as e:
                meta = PackageMetadata(name=n, ecosystem=ecosystem, exists=False, error=str(e))
            results[n] = meta
    for n in names:
        report = evaluate(results[n])
        reports.append(report)
        print_report(report)
    return reports


def parse_requirements_txt(path):
    names = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            m = re.match(r"^([A-Za-z0-9_.\-]+)", line)
            if m:
                names.append(m.group(1))
    return names


def parse_package_json(path):
    with open(path) as f:
        data = json.load(f)
    names = []
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        names.extend((data.get(key) or {}).keys())
    return names


def cmd_check(args):
    reports = run_check(args.packages, args.ecosystem)
    summarize(reports)


def cmd_scan(args):
    path = args.file
    if path.endswith(".json"):
        names = parse_package_json(path)
        ecosystem = "npm"
    else:
        names = parse_requirements_txt(path)
        ecosystem = "pypi"
    if not names:
        print("No packages found to scan.")
        return
    print(f"Scanning {len(names)} package(s) from {path} ({ecosystem})...\n")
    reports = run_check(names, ecosystem)
    summarize(reports)


def cmd_install(args):
    cmd = args.command
    if not cmd or cmd[0] not in ("npm", "pip", "pip3"):
        print("Usage: pkguard install <npm install ...|pip install ...>")
        sys.exit(1)
    ecosystem = "npm" if cmd[0] == "npm" else "pypi"
    pkg_names = [c for c in cmd[2:] if not c.startswith("-")]
    pkg_names = [re.match(r"^([A-Za-z0-9_.\-@/]+)", n).group(1) for n in pkg_names]
    if not pkg_names:
        print("No package names detected in command.")
        sys.exit(1)

    print(f"pkguard: validating {len(pkg_names)} package(s) before install...\n")
    reports = run_check(pkg_names, ecosystem)

    risky = [r for r in reports if not r.exists or r.risk_score >= 35]
    if risky:
        print(f"{BOLD}  {len(risky)} package(s) flagged as risky. Install blocked.{RESET}")
        print("Re-run with --force to install anyway, or remove the flagged packages.\n")
        if "--force" not in cmd:
            sys.exit(1)

    print(f"{GREEN}Proceeding with install...{RESET}\n")
    subprocess.run(cmd)


def summarize(reports):
    total = len(reports)
    missing = sum(1 for r in reports if not r.exists)
    risky = sum(1 for r in reports if r.exists and r.risk_score >= 35)
    ok = total - missing - risky
    line = "-" * 50
    print(line)
    print(f"{BOLD}Summary:{RESET} {total} checked  |  "
          f"{GREEN}{ok} ok{RESET}  |  "
          f"\033[93m{risky} risky{RESET}  |  "
          f"\033[91m{missing} not found{RESET}")


def main():
    parser = argparse.ArgumentParser(
        prog="pkguard",
        description="Validate packages before install to catch slopsquatting / hallucinated packages."
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_check = sub.add_parser("check", help="Check specific package names")
    p_check.add_argument("packages", nargs="+")
    p_check.add_argument("--ecosystem", choices=["npm", "pypi"], required=True)
    p_check.set_defaults(func=cmd_check)

    p_scan = sub.add_parser("scan", help="Scan a requirements.txt or package.json file")
    p_scan.add_argument("file")
    p_scan.set_defaults(func=cmd_scan)

    p_install = sub.add_parser("install", help="Wrap npm/pip install, validating first")
    p_install.add_argument("command", nargs=argparse.REMAINDER)
    p_install.set_defaults(func=cmd_install)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()