#!/usr/bin/env python3
"""Summarize Trivy image findings and gate high-severity issues."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BLOCKING_SEVERITIES = {"HIGH", "CRITICAL"}
CATEGORIES = (
    ("Vulnerability", "Vulnerabilities", "vulnerabilities"),
    ("Credential", "Secrets", "credential_rules"),
    ("Misconfiguration", "Misconfigurations", "misconfigurations"),
)


def evaluate(
    report: dict[str, Any],
) -> tuple[dict[str, int], list[dict[str, str]], list[dict[str, str]]]:
    counts = {name: 0 for _, _, name in CATEGORIES}
    findings: list[dict[str, str]] = []
    blockers: list[dict[str, str]] = []

    for result in report.get("Results") or []:
        target = str(result.get("Target") or "unknown")
        for category, field, count_name in CATEGORIES:
            for item in result.get(field) or []:
                counts[count_name] += 1
                severity = str(item.get("Severity") or "UNKNOWN").upper()
                if category == "Credential":
                    # Match and Code are deliberately never read; both may expose credentials.
                    identifier = str(item.get("RuleID") or "unknown")
                    title = str(item.get("Category") or "secret rule")
                else:
                    identifier = str(
                        item.get("VulnerabilityID")
                        or item.get("RuleID")
                        or item.get("ID")
                        or "unknown"
                    )
                    title = str(
                        item.get("PkgName")
                        or item.get("Title")
                        or identifier
                    )
                finding = {
                    "category": category,
                    "id": identifier,
                    "title": title,
                    "severity": severity,
                    "target": target,
                    "installed_version": (
                        str(item.get("InstalledVersion") or "")
                        if category == "Vulnerability" else ""
                    ),
                    "fixed_version": (
                        str(item.get("FixedVersion") or "")
                        if category == "Vulnerability" else ""
                    ),
                }
                findings.append(finding)

                is_blocking = severity in BLOCKING_SEVERITIES
                if category == "Vulnerability":
                    is_blocking = is_blocking and bool(finding["fixed_version"])
                if is_blocking:
                    blockers.append(finding)

    return counts, findings, blockers


def render_report(
    counts: dict[str, int],
    findings: list[dict[str, str]],
    blockers: list[dict[str, str]],
    mode: str,
) -> str:
    gate_counts = {
        name: sum(
            1
            for finding in blockers
            if (
                (name == "vulnerabilities" and finding["category"] == "Vulnerability")
                or (
                    name == "credential_rules"
                    and finding["category"] == "Credential"
                )
                or (
                    name == "misconfigurations"
                    and finding["category"] == "Misconfiguration"
                )
            )
        )
        for name in counts
    }
    lines = [
        "## 開発用イメージの検査結果",
        "",
        "| 区分 | 検出数 | 公開ゲート対象 |",
        "|---|---:|---:|",
        f"| 脆弱性 | {counts['vulnerabilities']} | {gate_counts['vulnerabilities']} |",
        f"| 秘密情報 | {counts['credential_rules']} | "
        f"{gate_counts['credential_rules']} |",
        f"| 設定不備 | {counts['misconfigurations']} | {gate_counts['misconfigurations']} |",
    ]
    severity_order = {name: rank for rank, name in enumerate(
        ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")
    )}
    reported = sorted(
        blockers if mode == "gate" else findings,
        key=lambda finding: (
            finding not in blockers,
            severity_order.get(finding["severity"], len(severity_order)),
        ),
    )
    if reported:
        lines.extend(("", "### 検出事項"))
        for finding in reported[:100]:
            fixed = (
                f"（修正版: `{finding['fixed_version']}`）"
                if finding["fixed_version"]
                else ""
            )
            lines.append(
                f"- {finding['severity']} {finding['category']} "
                f"`{finding['id']}`（{finding['title']}）、対象 "
                f"`{finding['target']}`{fixed}"
            )
        if len(reported) > 100:
            lines.append(f"- ほか {len(reported) - 100} 件は省略しました")
    elif mode == "gate":
        lines.extend(("", "公開ゲート対象の検出事項はありません。"))
    else:
        lines.extend(("", "検出事項はありません。"))
    return "\n".join(lines) + "\n"


def write_github_output(path: Path, findings: list[dict[str, str]]) -> None:
    with path.open("a", encoding="utf-8") as output:
        output.write(f"has_findings={'true' if findings else 'false'}\n")


def write_findings_json(
    path: Path,
    counts: dict[str, int],
    findings: list[dict[str, str]],
    blockers: list[dict[str, str]],
) -> None:
    path.write_text(json.dumps({
        "schema_version": 1,
        "counts": counts,
        "findings": findings,
        "blockers": blockers,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_report(report: dict[str, Any]) -> None:
    results = report.get("Results")
    if not isinstance(results, list) or not results or report.get("Error"):
        raise ValueError("Trivy scan has no verified results")
    for result in results:
        if (not isinstance(result, dict) or not isinstance(result.get("Target"), str)
                or not result["Target"].strip() or result.get("Error")):
            raise ValueError("Trivy scan target is unverified")
        for _, field, _ in CATEGORIES:
            items = result.get(field)
            if items is not None and (
                not isinstance(items, list) or any(not isinstance(item, dict) for item in items)
            ):
                raise ValueError("invalid Trivy findings")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("gate", "report"))
    parser.add_argument("report", type=Path)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--findings-json", type=Path)
    args = parser.parse_args()

    try:
        report = json.loads(args.report.read_text())
        if not isinstance(report, dict):
            raise ValueError("Trivy report must be a JSON object")
        validate_report(report)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: could not read Trivy report: {exc}", file=sys.stderr)
        return 2

    counts, findings, blockers = evaluate(report)
    if args.findings_json:
        write_findings_json(args.findings_json, counts, findings, blockers)
    print(render_report(counts, findings, blockers, args.mode), end="")
    if args.github_output:
        write_github_output(args.github_output, findings)
    return 1 if args.mode == "gate" and blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
