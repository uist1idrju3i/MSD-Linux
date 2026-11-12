#!/usr/bin/env python3
"""Combine sanitized native architecture scans without treating missing input as clean."""

import argparse
import json
from pathlib import Path
import re


ARCHES = ("amd64", "arm64")
COUNT_KEYS = {"vulnerabilities", "credential_rules", "misconfigurations"}


def collect(directory: Path, scan_result: str) -> tuple[str, bool, str]:
    complete = scan_result == "success"
    has_findings = False
    sections = []
    for arch in ARCHES:
        try:
            root = directory / arch
            status = json.loads((root / "scan-status.json").read_text())
            if status != {"arch": arch, "status": "success"}:
                raise ValueError("scan did not succeed")
            provenance = json.loads((root / "image-provenance.json").read_text())
            if (provenance.get("architecture") != arch or provenance.get("os") != "linux"
                    or not re.fullmatch(r"sha256:[0-9a-f]{64}", provenance.get("image_id", ""))):
                raise ValueError("image platform is unverified")
            findings = json.loads((root / "trivy-findings.json").read_text())
            counts = findings["counts"]
            if (findings.get("schema_version") != 1 or set(counts) != COUNT_KEYS
                    or any(type(n) is not int or n < 0 for n in counts.values())
                    or not isinstance(findings["findings"], list)
                    or sum(counts.values()) != len(findings["findings"])):
                raise ValueError("invalid findings")
            report = (root / "trivy-report.md").read_text()
            if not report.strip():
                raise ValueError("empty report")
            has_findings |= bool(findings["findings"])
            sections.append(f"## linux/{arch}\n\n" + report[:20000]
                            + ("\n\n全文はarch別artifactを参照してください。\n" if len(report) > 20000 else ""))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            complete = False
            sections.append(f"## linux/{arch}\n\n検査失敗または資料欠落のため未確認です。")
    status = "success" if complete else "failed"
    title = ("両archの検査が完了しました。" if complete
             else "監視に失敗しました。両archの完全な結果は未確認です。")
    return status, has_findings, title + "\n\n" + "\n\n".join(sections) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--scan-result", required=True)
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()
    status, has_findings, body = collect(args.directory, args.scan_result)
    args.body.write_text(body)
    with args.github_output.open("a") as output:
        output.write(f"status={status}\nhas_findings={str(has_findings).lower()}\n")
    print(body, end="")
    return 0 if status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
