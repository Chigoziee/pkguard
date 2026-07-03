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
import re
import sys
import concurrent.futures as cf

from .registries import check_package
from .heuristics import evaluate, RiskReport

SEVERITY_COLOR = {
    "critical": "\033[91m",  # red
    "high": "\033[91m",
    "medium": "\033[93m",    # yellow
    "low": "\033[94m",       # blue
    "info": "\033[90m",      # gray
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
                from .registries import PackageMetadata
                meta = PackageMetadata(name=n, ecosystem=ecosystem, exists=False, error=str(e))
            results[n] = meta
    # preserve input order
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
            # strip version specifiers / extras
            m = re.match(r"^([A-Za-z0-9_.\-]+)", line)
            if m:
                names.append(m.group(1))
    return names


def parse_package_json(path):
    import json
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
    # args.command is like ["npm", "install", "foo", "bar"] or ["pip", "install", "foo", "bar"]
    cmd = args.command
    if not cmd or cmd[0] not in ("npm", "pip", "pip3"):
        print("Usage: pkguard install <npm install ...|pip install ...>")
        sys.exit(1)
    ecosystem = "npm" if cmd[0] == "npm" else "pypi"
    # everything after 'install' that isn't a flag
    pkg_names = [c for c in cmd[2:] if not c.startswith("-")]
    pkg_names = [re.match(r"^([A-Za-z0-9_.\-@/]+)", n).group(1) for n in pkg_names]
    if not pkg_names:
        print("No package names detected in command.")
        sys.exit(1)

    print(f"pkguard: validating {len(pkg_names)} package(s) before install...\n")
    reports = run_check(pkg_names, ecosystem)

    risky = [r for r in reports if not r.exists or r.risk_score >= 35]
    if risky:
        print(f"{BOLD}⚠  {len(risky)} package(s) flagged as risky. Install blocked.{RESET}")
        print("Re-run with --force to install anyway, or remove the flagged packages.\n")
        if "--force" not in cmd:
            sys.exit(1)

    print(f"{GREEN}Proceeding with install...{RESET}\n")
    import subprocess
    subprocess.run(cmd)


def summarize(reports):
    total = len(reports)
    missing = sum(1 for r in reports if not r.exists)
    risky = sum(1 for r in reports if r.exists and r.risk_score >= 35)
    ok = total - missing - risky
    print("-" * 50)
    print(f"{BOLD}Summary:{RESET} {total} checked  |  "
          f"{GREEN}{ok} ok{RESET}  |  "
          f"\033[93m{risky} risky{RESET}  |  "
          f"\033[91m{missing} not found{RESET}")


def main():
    parser = argparse.ArgumentParser(prog="pkguard", description="Validate packages before install to catch slopsquatting / hallucinated packages.")
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
