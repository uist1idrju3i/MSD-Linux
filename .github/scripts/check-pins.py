#!/usr/bin/env python3
"""Check duplicated pins and report upstream versions."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

KERNEL_SERIES = "rpi-6.18.y"
ROOT = Path(__file__).resolve().parents[2]


def parse_ls_remote(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].startswith("refs/heads/"):
            result[fields[1][11:]] = fields[0]
    return result


def parse_release(data: str) -> str:
    value = json.loads(data)
    return str(value.get("tag_name") or value.get("name") or "")


def parse_runner_labels(text: str) -> list[tuple[str, str]]:
    labels: list[tuple[str, str]] = []
    for line in text.splitlines():
        for label in re.findall(r"`(ubuntu-\d+\.04(?:-arm)?(?:-preview)?)`", line):
            markers = [marker for marker in ("beta", "preview") if marker in line.lower()]
            labels.append((label, ", ".join(markers) or "listed"))
    return labels


def runner_label(root: Path) -> str:
    workflows = sorted((root / ".github/workflows").glob("*.yml"))
    for path in workflows:
        match = re.search(r"^\s*runs-on:\s*([^\s#]+)", path.read_text(), re.M)
        if match:
            return match.group(1)
    return ""


def parse_buildroot_branch(text: str) -> str:
    match = re.search(r'path = vendor/buildroot\s+url = .*?\s+branch = ([^\s]+)', text, re.S)
    return match.group(1) if match else ""


def branch_key(name: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", name))


def workflow_env(root: Path, workflow: str, key: str) -> str:
    text = (root / workflow).read_text()
    match = re.search(rf"^\s+{re.escape(key)}:\s*([^\s#]+)", text, re.M)
    return match.group(1) if match else ""


def run(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(
        args, cwd=cwd, text=True, stderr=subprocess.STDOUT, timeout=30
    )


def consistency(root: Path) -> list[str]:
    errors: list[str] = []
    definition = (root / "configs/msd_cardputerzero_defconfig").read_text()
    kernel_shas = re.findall(
        r"BR2_LINUX_KERNEL_CUSTOM_TARBALL_LOCATION=.*?linux-([0-9a-f]{40})\.tar\.gz",
        definition,
    )
    hash_files = list((root / "board/cardputerzero/patches/linux").glob("*.hash"))
    hash_names = [
        match.group(1)
        for path in hash_files
        for match in [re.search(r"linux-([0-9a-f]{40})\.tar\.gz", path.read_text())]
        if match
    ]
    if not kernel_shas or len(set(kernel_shas)) != 1:
        errors.append("defconfig kernel SHA values must be identical")
    if len(hash_names) != 1 or kernel_shas[:1] != hash_names:
        errors.append("defconfig kernel SHA must match linux.hash filename")

    makefile = (root / "package/m5stack-cardputerzero/m5stack-cardputerzero.mk").read_text()
    if re.search(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{40}(?![0-9A-Fa-f])", makefile):
        errors.append("m5stack-cardputerzero.mk must not contain a literal SHA")

    overlay = root / "vendor/m5stack-linux-dtoverlays"
    if (overlay / ".git").exists() or (overlay / "HEAD").exists():
        try:
            gitlink = run("git", "ls-tree", "HEAD", "vendor/m5stack-linux-dtoverlays", cwd=root).split()[2]
            actual = run("git", "-C", str(overlay), "rev-parse", "HEAD").strip()
            if actual != gitlink:
                errors.append("initialized dtoverlays submodule does not match its gitlink")
        except (IndexError, subprocess.CalledProcessError):
            errors.append("could not inspect dtoverlays submodule")

    runners = [
        match.group(1)
        for path in sorted((root / ".github/workflows").glob("*.yml"))
        for match in re.finditer(r"^\s*runs-on:\s*([^\s#]+)", path.read_text(), re.M)
    ]
    if not runners or len(set(runners)) != 1:
        errors.append("all workflow runs-on labels must be identical")
    actionlint = (root / ".github/actionlint.yaml").read_text()
    ignored = re.findall(r"label \"([^\"]+)\" is unknown", actionlint)
    if len(ignored) != 1 or (runners and ignored[0] != runners[0]):
        errors.append("actionlint ignored runner label differs from workflows")

    readme = (root / "README.md").read_text()
    readme_version = re.search(r"\| ビルド \| Buildroot ([0-9.]+) \|", readme)
    branch = parse_buildroot_branch((root / ".gitmodules").read_text())
    if not readme_version or readme_version.group(1) != branch.removesuffix(".x"):
        errors.append("README Buildroot version differs from .gitmodules")
    return errors


def fetch(url: str) -> str:
    request = Request(url, headers={"Accept": "application/vnd.github+json"})
    if os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urlopen(request, timeout=20) as response:
        return response.read().decode()


def upstream(report_path: Path, root: Path) -> int:
    rows: list[tuple[str, str, str, str, str]] = []
    fixed = "unknown"
    definition = (root / "configs/msd_cardputerzero_defconfig").read_text()
    match = re.search(r"linux-([0-9a-f]{40})\.tar\.gz", definition)
    if match:
        fixed = match.group(1)
    try:
        refs = parse_ls_remote(run(
            "git", "ls-remote", "https://github.com/raspberrypi/linux.git",
            "refs/heads/rpi-*.y",
        ))
        series = f"rpi-{KERNEL_SERIES[4:]}"
        latest = refs.get(series, "")
        rows.append(("Raspberry Pi Linux", fixed, latest or "確認できず",
                     "確認できず" if not latest else ("最新" if latest == fixed else "更新あり"),
                     "https://github.com/raspberrypi/linux"))
        branches = [name for name in refs if re.fullmatch(r"rpi-\d+\.\d+\.y", name)]
        newest = max(branches, key=branch_key) if branches else "確認できず"
        rows.append(("Raspberry Pi Linux series", series, newest,
                     "参考",
                     "https://github.com/raspberrypi/linux/branches"))
    except (OSError, URLError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        rows.append(("Raspberry Pi Linux", fixed, "確認できず", "確認できず", "https://github.com/raspberrypi/linux"))
        rows.append(("Raspberry Pi Linux series", KERNEL_SERIES, "確認できず", "参考",
                     "https://github.com/raspberrypi/linux/branches"))
    branch = parse_buildroot_branch((root / ".gitmodules").read_text())
    try:
        refs = parse_ls_remote(run(
            "git", "ls-remote", "--heads", "https://gitlab.com/buildroot.org/buildroot.git",
        ))
        branches = [name for name in refs if re.fullmatch(r"\d{4}\.\d{2}\.x", name)]
        newest = max(branches, key=branch_key) if branches else "確認できず"
        lts = [name for name in branches if name.endswith(".02.x")]
        newest_lts = max(lts, key=branch_key) if lts else "確認できず"
        current = branch_key(branch) >= branch_key(newest) if newest != "確認できず" else False
        status = "確認できず" if newest == "確認できず" else ("最新" if current else "更新あり")
        rows.append(("Buildroot", branch, newest, status,
                     "https://gitlab.com/buildroot.org/buildroot/-/branches"))
        rows.append(("Buildroot LTS", branch, newest_lts, "参考",
                     "https://gitlab.com/buildroot.org/buildroot/-/branches"))
    except (OSError, URLError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        rows.append(("Buildroot", branch, "確認できず", "確認できず",
                     "https://gitlab.com/buildroot.org/buildroot/-/branches"))
        rows.append(("Buildroot LTS", branch, "確認できず", "参考",
                     "https://gitlab.com/buildroot.org/buildroot/-/branches"))

    for name, repository, env_name in (
        ("actionlint", "rhysd/actionlint", "ACTIONLINT_VERSION"),
        ("ShellCheck", "koalaman/shellcheck", "SHELLCHECK_VERSION"),
        ("kernel-hardening-checker", "a13xp0p0v/kernel-hardening-checker", "KHC_TAG"),
    ):
        workflow, env_key = (
            (".github/workflows/build.yml", env_name)
            if env_name.startswith("KHC_")
            else (".github/workflows/lint.yml", env_name)
        )
        pin = os.environ.get(env_name) or workflow_env(root, workflow, env_key) or "未設定"
        pinned_value = pin
        if env_name == "KHC_TAG":
            commit = os.environ.get("KHC_COMMIT") or workflow_env(
                root, ".github/workflows/build.yml", "KHC_COMMIT"
            )
            if commit:
                pinned_value = f"{pin} ({commit})"
        try:
            latest = parse_release(fetch(f"https://api.github.com/repos/{repository}/releases/latest"))
            status = "最新" if pin.lstrip("v") == latest.lstrip("v") else "更新あり"
        except (OSError, URLError, ValueError) as exc:
            print(f"{name}: upstream check unavailable: {exc}", file=sys.stderr)
            latest, status = "確認できず", "確認できず"
        rows.append((name, pinned_value, latest, status, f"https://github.com/{repository}/releases"))

    try:
        image_readme = fetch("https://raw.githubusercontent.com/actions/runner-images/main/README.md")
        labels = parse_runner_labels(image_readme)
        names = sorted({label for label, _ in labels})
        standard_names = [label for label in names if "-arm" not in label]
        if standard_names:
            names = standard_names
        newest = max(names, key=branch_key) if names else "確認できず"
        pinned = os.environ.get("RUNNER_LABEL") or runner_label(root) or "未設定"
        state = "掲載あり" if any(label == pinned for label, _ in labels) else "掲載なし"
        status = (
            "確認できず"
            if newest == "確認できず"
            else ("最新" if pinned == newest else "更新あり")
        )
        label_list = ", ".join(
            f"{label} ({marker})" if marker != "listed" else label
            for label, marker in labels
        )
        rows.append(("GitHub-hosted runner", pinned,
                     f"最新: {newest}; 固定値: {state}; labels: {label_list}", status,
                     "https://github.com/actions/runner-images"))
    except (OSError, URLError, ValueError):
        rows.append(("GitHub-hosted runner", os.environ.get("RUNNER_LABEL") or runner_label(root) or "未設定",
                     "確認できず", "確認できず", "https://github.com/actions/runner-images"))
    lines = ["| 依存 | 固定値 | 最新 | 状態(最新・更新あり・確認できず・参考) | 参照URL |",
             "|---|---|---|---|---|"]
    lines.extend(f"| {name} | `{pin}` | `{latest}` | {status} | {url} |"
                 for name, pin, latest, status, url in rows)
    report_path.write_text("\n".join(lines) + "\n")
    print("更新あり" if any(row[3] not in {"最新", "参考"} for row in rows) else "全て最新")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("consistency")
    upstream_parser = subparsers.add_parser("upstream")
    upstream_parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "consistency":
        errors = consistency(ROOT)
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1 if errors else 0
    return upstream(args.report, ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
