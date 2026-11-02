#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"

python3 - "${repo_root}" <<'PY'
import importlib.util
import json
import os
import pathlib
import re
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
    "Metadata": {"ImageConfig": {"Env": ["TOKEN=AKIAFAKEMARKER"]}},
    "Results": [
        {
            "Target": "debian 13",
            "Vulnerabilities": [
                {
                    "VulnerabilityID": "CVE-2026-1000",
                    "PkgName": "libsample",
                    "Severity": "HIGH",
                    "InstalledVersion": "1.2.2",
                    "Description": "AKIAFAKEMARKER",
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
                    "InstalledVersion": "AKIAFAKEMARKER",
                    "FixedVersion": "AKIAFAKEMARKER",
                }
            ],
            "Misconfigurations": [
                {
                    "ID": "DS-0001",
                    "Title": "Weak setting",
                    "Severity": "CRITICAL",
                    "Message": "AKIAFAKEMARKER",
                    "CauseMetadata": {"Code": "AKIAFAKEMARKER"},
                },
                {
                    "ID": "DS-0002",
                    "Severity": "LOW",
                    "Message": "AKIAFAKEMARKER",
                }
            ],
        }
    ]
}
counts, findings, blockers = module.evaluate(report)
assert counts == {
    "vulnerabilities": 3,
    "credential_rules": 1,
    "misconfigurations": 2,
}
assert len(findings) == 6
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

long_report = {
    "Results": [{"Vulnerabilities": [
        {"VulnerabilityID": f"CVE-low-{i}", "Severity": "LOW"}
        for i in range(120)
    ] + [
        {"VulnerabilityID": "CVE-critical-no-fix", "Severity": "CRITICAL"},
        {"VulnerabilityID": "CVE-blocking-high", "Severity": "HIGH",
         "FixedVersion": "2.0"},
        {"VulnerabilityID": "CVE-blocking-critical", "Severity": "CRITICAL",
         "FixedVersion": "2.0"},
        {"VulnerabilityID": "CVE-unknown", "Severity": "UNRECOGNIZED"},
    ]}]
}
long_counts, long_findings, long_blockers = module.evaluate(long_report)
prioritized = module.render_report(long_counts, long_findings, long_blockers, "report")
assert prioritized.index("CVE-blocking-critical") < prioritized.index("CVE-blocking-high")
assert prioritized.index("CVE-blocking-high") < prioritized.index("CVE-critical-no-fix")
assert prioritized.index("CVE-critical-no-fix") < prioritized.index("CVE-low-0")
assert "ほか 24 件" in prioritized
assert len(long_findings) == 124

empty_counts, empty_findings, empty_blockers = module.evaluate({"Results": []})
assert not any(empty_counts.values())
assert empty_findings == empty_blockers == []
assert "検出事項はありません" in module.render_report(
    empty_counts, empty_findings, empty_blockers, "report"
)

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
        [sys.executable, str(script), "report", str(report_path),
         "--findings-json", str(pathlib.Path(directory) / "findings.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert report_mode.returncode == 0
    assert "AKIAFAKEMARKER" not in report_mode.stdout
    safe_json = (pathlib.Path(directory) / "findings.json").read_text()
    assert "AKIAFAKEMARKER" not in safe_json
    safe = json.loads(safe_json)
    assert safe["schema_version"] == 1
    assert safe["counts"] == counts
    assert len(safe["findings"]) == 6
    assert len(safe["blockers"]) == 3
    assert safe["findings"][0]["installed_version"] == "1.2.2"
    assert safe["findings"][0]["fixed_version"] == "1.2.3"
    module.write_findings_json(pathlib.Path(directory) / "all.json", long_counts,
                               long_findings, long_blockers)
    all_findings = json.loads((pathlib.Path(directory) / "all.json").read_text())
    assert len(all_findings["findings"]) == 124
    assert len(all_findings["blockers"]) == 2
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
print("ok - blocking findings precede severity-sorted truncated details")
print("ok - sanitized JSON preserves all findings and no secret payloads")


def workflow_step(workflow, name):
    match = re.search(rf"(?m)^\s+(?:- )?name: {re.escape(name)}\s*$",
                      workflow.read_text())
    assert match, name
    body = workflow.read_text()[match.end():]
    source = body.split("        run: |\n", 1)[1]
    lines = []
    for line in source.splitlines():
        if line and not line.startswith("          "):
            break
        lines.append(line[10:] if line else "")
    assert lines, name
    return "\n".join(lines) + "\n"


publisher = root / ".github/workflows/publish-dev-image.yml"
artifact = publisher.read_text().split("name: msd-dev-trivy-${{ matrix.arch }}", 1)[1]
artifact = artifact.split("\n      - ", 1)[0]
paths = artifact.split("path: |\n", 1)[1].split("if-no-files-found:", 1)[0]
assert {line.strip() for line in paths.splitlines() if line.strip()} == {
    "${{ runner.temp }}/trivy-findings.json",
    "${{ runner.temp }}/trivy-report.md",
    "${{ runner.temp }}/image-provenance.json",
    "${{ runner.temp }}/trivy-version.txt",
    "${{ runner.temp }}/sbom.spdx.json",
}

with tempfile.TemporaryDirectory() as directory:
    temp = pathlib.Path(directory)
    binary = temp / "bin"
    binary.mkdir()
    docker = binary / "docker"
    docker.write_text('''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
args = sys.argv[1:]
with open(os.environ["DOCKER_CALLS"], "a") as log:
    log.write(args[0] + "\\n")
if args[0] == "pull":
    if os.environ.get("PULL_FAILURE"):
        print(os.environ["PULL_FAILURE"], file=sys.stderr)
        sys.exit(1)
elif args[:2] == ["image", "inspect"]:
    if args[-1] == "{{.Id}}":
        print("sha256:" + "a" * 64)
    else:
        print(json.dumps({"image_id": "sha256:" + "a" * 64}))
elif args[0] == "save":
    Path(args[args.index("--output") + 1]).write_bytes(b"fixture")
elif args[0] == "run":
    print("Version: fixture")
else:
    raise SystemExit("unexpected docker command")
''', encoding="utf-8")
    docker.chmod(0o755)
    environment = dict(os.environ, PATH=f"{binary}:{os.environ['PATH']}")
    pull_script = workflow_step(
        root / ".github/workflows/dev-image-scan.yml", "Pull latest development image"
    )
    for index, failure in enumerate(("manifest unknown", "unauthorized", "network timeout", "")):
        run_dir = temp / str(index)
        run_dir.mkdir()
        output = run_dir / "output"
        calls = run_dir / "docker-calls"
        env = dict(environment, RUNNER_TEMP=str(run_dir), GITHUB_OUTPUT=str(output),
                   IMAGE="example.invalid/image:latest", DOCKER_CALLS=str(calls),
                   PULL_FAILURE=failure)
        pulled = subprocess.run(["bash", "-euo", "pipefail", "-c", pull_script],
                                cwd=root, env=env, capture_output=True, text=True)
        if failure:
            assert pulled.returncode != 0
            assert not output.exists()
            assert calls.read_text() == "pull\n"
        else:
            assert pulled.returncode == 0, pulled.stderr
            assert output.read_text() == "image_available=true\n"
            assert (run_dir / "msd-dev.tar").is_file()
            assert json.loads((run_dir / "image-provenance.json").read_text())["image_id"]

    (temp / "trivy.json").write_text(json.dumps(report), encoding="utf-8")
    prepared = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", workflow_step(publisher, "Prepare sanitized scan findings")],
        cwd=root, env=dict(environment, RUNNER_TEMP=str(temp), DOCKER_CALLS=str(temp / "calls"),
                           TRIVY_VERSION="fixture", TRIVY_DIGEST="sha256:" + "a" * 64),
        capture_output=True, text=True,
    )
    assert prepared.returncode == 0, prepared.stderr
    for name in ("trivy-findings.json", "trivy-report.md", "image-provenance.json", "trivy-version.txt"):
        assert "AKIAFAKEMARKER" not in (temp / name).read_text()
    selected = json.loads((temp / "trivy-findings.json").read_text())
    assert selected["counts"] == counts and len(selected["findings"]) == 6
print("ok - publisher artifacts exclude raw scan JSON and actual report step filters payloads")
print("ok - pull failures stay failed; a successful pull records the image and enables scanning")
PY
