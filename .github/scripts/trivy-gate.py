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
    ("Secret", "Secrets", "secrets"),
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
                identifier = str(
                    item.get("VulnerabilityID")
                    or item.get("RuleID")
                    or item.get("ID")
                    or "unknown"
                )
                title = str(
                    item.get("PkgName")
                    or item.get("Title")
                    or item.get("Message")
                    or identifier
                )
                finding = {
                    "category": category,
                    "id": identifier,
                    "title": title,
                    "severity": severity,
                    "target": target,
                    "fixed_version": str(item.get("FixedVersion") or ""),
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
                or (name == "secrets" and finding["category"] == "Secret")
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
        f"| 秘密情報 | {counts['secrets']} | {gate_counts['secrets']} |",
        f"| 設定不備 | {counts['misconfigurations']} | {gate_counts['misconfigurations']} |",
    ]
    reported = blockers if mode == "gate" else findings
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("gate", "report"))
    parser.add_argument("report", type=Path)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    try:
        report = json.loads(args.report.read_text())
        if not isinstance(report, dict):
            raise ValueError("Trivy report must be a JSON object")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: could not read Trivy report: {exc}", file=sys.stderr)
        return 2

    counts, findings, blockers = evaluate(report)
    print(render_report(counts, findings, blockers, args.mode), end="")
    if args.github_output:
        write_github_output(args.github_output, findings)
    return 1 if args.mode == "gate" and blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
