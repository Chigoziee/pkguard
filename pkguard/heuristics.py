"""
Risk scoring heuristics applied to package metadata.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from .registries import PackageMetadata
from .popular import get_popular_set


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
    severity: str  # "critical", "high", "medium", "low", "info"
    reason: str


@dataclass
class RiskReport:
    package: str
    ecosystem: str
    exists: bool
    findings: List[RiskFinding] = field(default_factory=list)
    risk_score: int = 0  # 0-100, higher = riskier

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

    # Typosquat / hallucination-lookalike check
    closest, dist = _closest_popular_match(meta.name, meta.ecosystem)
    if closest is not None and dist <= 2 and meta.name.lower() != closest.lower():
        report.findings.append(RiskFinding(
            "critical",
            f"Name is suspiciously close to popular package '{closest}' "
            f"(edit distance {dist}). Possible typosquat."
        ))
        score += 40

    # Age check
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

    # Version count (single version = less scrutiny/history)
    if meta.version_count <= 1:
        report.findings.append(RiskFinding("medium", "Only one published version — little history to evaluate."))
        score += 10

    # Maintainer count
    if meta.maintainer_count == 0:
        report.findings.append(RiskFinding("medium", "No identifiable maintainer information."))
        score += 10
    elif meta.maintainer_count == 1:
        report.findings.append(RiskFinding("low", "Single maintainer (not necessarily bad, but higher single-point risk)."))
        score += 3

    # Repository / license presence
    if not meta.has_repository:
        report.findings.append(RiskFinding("medium", "No linked source repository."))
        score += 10
    if not meta.has_license:
        report.findings.append(RiskFinding("low", "No license declared."))
        score += 5

    # Description
    if not meta.description or len(meta.description.strip()) < 10:
        report.findings.append(RiskFinding("low", "Missing or very sparse package description."))
        score += 5

    # Downloads (npm only, when available)
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
