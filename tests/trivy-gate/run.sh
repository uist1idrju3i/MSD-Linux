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
    assert args[args.index("--platform") + 1] == "linux/" + os.environ["ARCH"]
    if os.environ.get("PULL_FAILURE"):
        print(os.environ["PULL_FAILURE"], file=sys.stderr)
        sys.exit(1)
elif args[:2] == ["image", "inspect"]:
    if args[-1] == "{{.Id}}":
        print(os.environ.get("IMAGE_ID", "sha256:" + "a" * 64))
    elif args[-1] == "{{.Architecture}}":
        print(os.environ.get("IMAGE_ARCH", os.environ["ARCH"]))
    elif args[-1] == "{{.Os}}":
        print(os.environ.get("IMAGE_OS", "linux"))
    else:
        print(json.dumps({"image_id": "sha256:" + "a" * 64}))
elif args[0] == "save":
    Path(args[args.index("--output") + 1]).write_bytes(b"fixture")
elif args[0] == "run":
    print("Version: fixture")
elif args[0] == "load":
    assert Path(args[args.index("--input") + 1]).is_file()
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
        env = dict(environment, RUNNER_TEMP=str(run_dir), GITHUB_OUTPUT=str(output), ARCH="arm64",
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
    for payload, expected in ((report, 1), (clean_report, 0)):
        (temp / "trivy.json").write_text(json.dumps(payload), encoding="utf-8")
        summary = temp / "summary.md"
        summary.write_text("", encoding="utf-8")
        gated = subprocess.run(
            ["bash", "-e", "-c", workflow_step(publisher, "Gate image findings")],
            cwd=root, env=dict(os.environ, RUNNER_TEMP=str(temp), GITHUB_STEP_SUMMARY=str(summary)),
            capture_output=True, text=True,
        )
        assert gated.returncode == expected, (gated.returncode, gated.stderr)
        assert summary.read_text() == (temp / "trivy-gate.md").read_text()
        assert summary.read_text() and "AKIAFAKEMARKER" not in summary.read_text()
    (temp / "trivy.json").write_text("invalid JSON", encoding="utf-8")
    failed_report = subprocess.run(
        ["bash", "-e", "-c", workflow_step(
            root / ".github/workflows/dev-image-scan.yml", "Report latest image findings")],
        cwd=root, env=dict(os.environ, RUNNER_TEMP=str(temp),
                           GITHUB_OUTPUT=str(temp / "report-output"),
                           GITHUB_STEP_SUMMARY=str(temp / "report-summary")),
        capture_output=True, text=True,
    )
    assert failed_report.returncode != 0
    (temp / "image").mkdir()
    (temp / "scan").mkdir()
    (temp / "image" / "msd-dev.tar.gz").write_bytes(b"fixture")
    (temp / "scan" / "image-provenance.json").write_text(
        json.dumps({"image_id": "sha256:" + "a" * 64}))
    for overrides, expected in (
        ({}, 0), ({"IMAGE_ID": "sha256:" + "b" * 64}, 1),
        ({"IMAGE_ARCH": "amd64"}, 1), ({"IMAGE_OS": "windows"}, 1),
    ):
        calls = temp / "transfer-calls"
        calls.write_text("")
        loaded = subprocess.run(
            ["bash", "-euo", "pipefail", "-c", workflow_step(
                publisher, "Load checked image without running it")],
            env=dict(environment, RUNNER_TEMP=str(temp), ARCH="arm64",
                     DOCKER_CALLS=str(calls), **overrides), capture_output=True, text=True)
        assert loaded.returncode == expected, loaded.stderr
        assert "run" not in calls.read_text().splitlines()
    (temp / "image" / "msd-dev.tar.gz").unlink()
    missing = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", workflow_step(
            publisher, "Load checked image without running it")],
        env=dict(environment, RUNNER_TEMP=str(temp), ARCH="arm64",
                 DOCKER_CALLS=str(temp / "transfer-calls")), capture_output=True, text=True)
    assert missing.returncode != 0
print("ok - publish loads without executing the image and rejects missing or mismatched transfers")
print("ok - publisher artifacts exclude raw scan JSON and actual report step filters payloads")
print("ok - pull failures stay failed; a successful pull records the image and enables scanning")
print("ok - publisher gate preserves failures through tee under GitHub's default bash shell")

aggregate_spec = importlib.util.spec_from_file_location(
    "dev_image_report", root / ".github/scripts/dev-image-report.py")
aggregate = importlib.util.module_from_spec(aggregate_spec)
aggregate_spec.loader.exec_module(aggregate)
with tempfile.TemporaryDirectory() as directory:
    temp = pathlib.Path(directory)
    def fixture(arch, entries):
        folder = temp / arch
        folder.mkdir(exist_ok=True)
        (folder / "scan-status.json").write_text(json.dumps({"arch": arch, "status": "success"}))
        (folder / "image-provenance.json").write_text(json.dumps({
            "architecture": arch, "os": "linux", "image_id": "sha256:" + "a" * 64}))
        (folder / "trivy-findings.json").write_text(json.dumps({
            "schema_version": 1, "findings": entries,
            "counts": {"vulnerabilities": len(entries), "credential_rules": 0,
                       "misconfigurations": 0}}))
        (folder / "trivy-report.md").write_text("fixture report\n")
    fixture("amd64", [])
    fixture("arm64", [])
    assert aggregate.collect(temp, "success")[:2] == ("success", False)
    fixture("arm64", [{"id": "CVE-arm64-only"}])
    status, found, body = aggregate.collect(temp, "success")
    assert (status, found) == ("success", True)
    assert "linux/amd64" in body and "linux/arm64" in body
    for name, payload in (("scan-status.json", '{"arch":"arm64","status":"failed"}'),
                          ("scan-status.json", 'invalid JSON'),
                          ("image-provenance.json", '{"architecture":"amd64"}'),
                          ("trivy-findings.json", '{"schema_version":1,"counts":{}}'),
                          ("trivy-report.md", "")):
        fixture("arm64", [])
        (temp / "arm64" / name).write_text(payload)
        assert aggregate.collect(temp, "success")[0] == "failed", name
    fixture("arm64", [])
    assert aggregate.collect(temp, "failure")[0] == "failed"
    (temp / "arm64" / "scan-status.json").unlink()
    assert aggregate.collect(temp, "success")[0] == "failed"
    result = subprocess.run([
        sys.executable, str(root / ".github/scripts/dev-image-report.py"), str(temp),
        "--scan-result", "failure", "--body", str(temp / "body"),
        "--github-output", str(temp / "outputs")], capture_output=True, text=True)
    assert result.returncode == 1
    assert "status=failed" in (temp / "outputs").read_text()
    assert "未確認" in (temp / "body").read_text()
print("ok - both architecture reports distinguish clean, arm64-only findings and missing or failed scans")

scan_workflow = (root / ".github/workflows/dev-image-scan.yml").read_text()
scan_job = scan_workflow.split("\n  scan:\n", 1)[1].split("\n  report:\n", 1)[0]
assert "arch: amd64" in scan_job and "arch: arm64" in scan_job
assert "runner: ubuntu-26.04-arm" in scan_job and "fail-fast: false" in scan_job
assert "issues: write" not in scan_job
assert "development-image-findings-${{ matrix.arch }}" in scan_job
assert "--paginate --slurp" in scan_workflow
assert "Issue本文は最後に確認できた結果です" in scan_workflow
issue_script = workflow_step(root / ".github/workflows/dev-image-scan.yml",
                             "Maintain vulnerability issue")
assert issue_script.startswith("set -euo pipefail\n")
guard = re.search(r'if (\[\[ "\$SCAN_STATUS".*?\]\]); then', issue_script, re.S)[1]
for status, findings_flag, expected in (
    ("success", "true", "verified"), ("success", "false", "verified"),
    ("failed", "false", "failed"), ("", "", "failed"),
    ("success", "", "failed"), ("success", "invalid", "failed"),
):
    checked = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", f"if {guard}; then echo failed; else echo verified; fi"],
        env=dict(os.environ, SCAN_STATUS=status, HAS_FINDINGS=findings_flag),
        capture_output=True, text=True)
    assert checked.returncode == 0 and checked.stdout.strip() == expected
print("ok - missing or invalid aggregate outputs cannot close the monitoring issue")

publication = publisher.read_text()
build_job = publication.split("\n  build:\n", 1)[1].split("\n  publish-arch:\n", 1)[0]
assert "packages: write" not in build_job and "id-token: write" not in build_job
assert "attestations: write" not in build_job
assert "docker push" not in build_job and "attest-sbom@" not in build_job
for name in ("publish-arch", "publish"):
    job = publication.split(f"\n  {name}:\n", 1)[1].split("\n  gate:\n", 1)[0]
    assert "if: github.ref == 'refs/heads/main'" in job
    assert "packages: write" in job and "id-token: write" in job
plan_script = workflow_step(publisher, "Plan image publication")
plan_script = plan_script.split("changed=true", 1)[0] + 'printf "%s" "$push"'
with tempfile.TemporaryDirectory() as directory:
    temp = pathlib.Path(directory)
    (temp / "docker").write_text("#!/bin/sh\nprintf fixture-tag\n")
    (temp / "docker").chmod(0o755)
    for event, ref, dry_run, expected in (
        ("push", "refs/heads/main", "", "true"),
        ("push", "refs/heads/other", "", "false"),
        ("workflow_dispatch", "refs/heads/main", "false", "true"),
        ("workflow_dispatch", "refs/heads/main", "true", "false"),
        ("workflow_dispatch", "refs/heads/other", "false", "false"),
        ("pull_request", "refs/pull/1/merge", "", "false"),
    ):
        env = dict(os.environ, PATH=f"{temp}:{os.environ['PATH']}",
                   EVENT_NAME=event, EVENT_REF=ref, DRY_RUN=dry_run)
        # Avoid the wrapper path, so the plan uses the isolated docker stub.
        command = plan_script.replace("docker/msd-dev tag", "docker tag")
        result = subprocess.run(["bash", "-euo", "pipefail", "-c", command],
                                env=env, capture_output=True, text=True)
        assert result.returncode == 0 and result.stdout == expected, (event, ref, result.stderr)
print("ok - publication is main-only; builds are read-only and cannot push or attest")
PY
