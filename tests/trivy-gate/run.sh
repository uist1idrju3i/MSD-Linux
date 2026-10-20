#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"

python3 - "${repo_root}" <<'PY'
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from io import StringIO

root = pathlib.Path(sys.argv[1])
script = root / ".github/scripts/trivy-gate.py"
spec = importlib.util.spec_from_file_location("trivy_gate", script)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

report = {
    "Results": [
        {
            "Target": "debian 13",
            "Vulnerabilities": [
                {
                    "VulnerabilityID": "CVE-2026-1000",
                    "PkgName": "libsample",
                    "Severity": "HIGH",
                    "FixedVersion": "1.2.3",
                },
                {
                    "VulnerabilityID": "CVE-2026-1001",
                    "PkgName": "libother",
                    "Severity": "CRITICAL",
                    "FixedVersion": "",
                },
                {
                    "VulnerabilityID": "CVE-2026-1002",
                    "PkgName": "libmedium",
                    "Severity": "MEDIUM",
                    "FixedVersion": "4.5.6",
                },
            ],
            "Secrets": [
                {
                    "RuleID": "generic-secret",
                    "Category": "cloud credential",
                    "PkgName": "AKIAFAKEMARKER",
                    "Title": "AKIAFAKEMARKER",
                    "Message": "AKIAFAKEMARKER",
                    "Severity": "HIGH",
                    "Match": "AKIAFAKEMARKER",
                    "Code": {"Lines": [{"Content": "AKIAFAKEMARKER"}]},
                }
            ],
            "Misconfigurations": [
                {
                    "ID": "DS-0001",
                    "Title": "Weak setting",
                    "Severity": "CRITICAL",
                }
            ],
        }
    ]
}
counts, findings, blockers = module.evaluate(report)
assert counts == {
    "vulnerabilities": 3,
    "credential_rules": 1,
    "misconfigurations": 1,
}
assert len(findings) == 5
assert [finding["id"] for finding in blockers] == [
    "CVE-2026-1000",
    "generic-secret",
    "DS-0001",
]
credential_finding = next(
    finding for finding in findings if finding["category"] == "Credential"
)
assert credential_finding["title"] == "cloud credential"
gate_report = module.render_report(counts, findings, blockers, "gate")
assert "CVE-2026-1000" in gate_report
assert "| 秘密情報 | 1 | 1 |" in gate_report
assert "AKIAFAKEMARKER" not in gate_report
assert "CVE-2026-1001" not in gate_report
full_report = module.render_report(counts, findings, blockers, "report")
assert "CVE-2026-1001" in full_report
assert "AKIAFAKEMARKER" not in full_report

with tempfile.TemporaryDirectory() as directory:
    output = pathlib.Path(directory) / "github-output"
    module.write_github_output(output, findings)
    assert output.read_text() == "has_findings=true\n"
    output.write_text("")
    module.write_github_output(output, [])
    assert output.read_text() == "has_findings=false\n"
    report_path = pathlib.Path(directory) / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    gated = subprocess.run(
        [sys.executable, str(script), "gate", str(report_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert gated.returncode == 1
    assert "AKIAFAKEMARKER" not in gated.stdout
    report_mode = subprocess.run(
        [sys.executable, str(script), "report", str(report_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert report_mode.returncode == 0
    assert "AKIAFAKEMARKER" not in report_mode.stdout
    clean_report = {
        "Results": [
            {
                "Target": "debian 13",
                "Vulnerabilities": [
                    {"Severity": "HIGH", "FixedVersion": ""},
                    {"Severity": "MEDIUM", "FixedVersion": "1.0"},
                ],
                "Secrets": [{"Severity": "LOW"}],
                "Misconfigurations": [{"Severity": "MEDIUM"}],
            }
        ]
    }
    report_path.write_text(json.dumps(clean_report), encoding="utf-8")
    clean_gate = subprocess.run(
        [sys.executable, str(script), "gate", str(report_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert clean_gate.returncode == 0

print("ok - gates only fixable high and critical vulnerabilities")
print("ok - gates high and critical secrets and misconfigurations")
print("ok - reports do not disclose detected secret values")
print("ok - reports findings without gating in report mode")
print("ok - command exits nonzero only for blocking findings")
PY
