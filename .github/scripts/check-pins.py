#!/usr/bin/env python3
"""Check duplicated pins and report upstream versions."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
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


def selected_bootlin_option(definition: str) -> str:
    options = re.findall(
        r"^(BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_[A-Z0-9_]+)=y$", definition, re.M
    )
    return options[0] if len(options) == 1 else ""


def bootlin_option_block(text: str, option: str) -> str | None:
    match = re.search(
        rf"^config {re.escape(option)}[ \t]*\n(.*?)(?=^config\s|\Z)",
        text,
        re.M | re.S,
    )
    return match.group(1) if match else None


def parse_bootlin_option_version(text: str, option: str) -> str:
    block = bootlin_option_block(text, option)
    if block is None:
        return ""
    match = re.search(
        r'^[ \t]*bool\s+"[^"]*?(\d{4}\.\d{2}-\d+)"[ \t]*$', block, re.M
    )
    return match.group(1) if match else ""


def parse_bootlin_latest(html: str) -> str:
    versions = re.findall(
        r"aarch64--glibc--stable-(\d{4}\.\d{2}-\d+)\.tar\.xz", html
    )
    return max(versions, key=branch_key) if versions else ""


def bootlin_status(
    pinned: str, latest: str, offered: str | None, stable_branch: str
) -> tuple[str, str]:
    version_pattern = r"\d{4}\.\d{2}-\d+"
    if not latest or not re.fullmatch(version_pattern, latest):
        return "確認できず", "確認できず"
    if offered is None:
        return latest, "確認できず"
    if not re.fullmatch(version_pattern, pinned):
        return latest, "確認できず"
    if offered and not re.fullmatch(version_pattern, offered):
        return latest, "確認できず"
    if not re.fullmatch(r"\d{4}\.\d{2}\.x", stable_branch):
        return latest, "確認できず"
    if pinned == latest:
        return latest, "最新"
    if offered and branch_key(offered) > branch_key(pinned):
        available = (
            f"Buildroot {stable_branch} で選択可"
            if offered == latest
            else f"Buildroot {stable_branch} で {offered} を選択可"
        )
        return f"{latest}（{available}）", "更新あり"
    return f"{latest}（安定版の Buildroot では未提供）", "Buildroot 安定版待ち"


def parse_buildroot_point_release(text: str, branch: str) -> tuple[str, str]:
    match = re.fullmatch(r"(\d{4}\.\d{2})\.x", branch)
    if not match:
        return "", ""
    series = match.group(1)
    tag_commits: dict[str, str] = {}
    tag_objects: dict[str, str] = {}
    tag_versions: dict[str, int] = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 2:
            continue
        sha, ref = fields
        peeled = ref.endswith("^{}")
        tag_ref = ref[:-3] if peeled else ref
        tag_match = re.fullmatch(
            rf"refs/tags/{re.escape(series)}(?:\.(\d+))?", tag_ref
        )
        if not tag_match:
            continue
        tag = tag_ref.removeprefix("refs/tags/")
        tag_versions[tag] = int(tag_match.group(1) or 0)
        if peeled:
            tag_commits[tag] = sha
        else:
            tag_objects[tag] = sha
    tags = set(tag_commits) | set(tag_objects)
    if not tags:
        return "", ""
    latest = max(tags, key=tag_versions.__getitem__)
    return latest, tag_commits.get(latest, tag_objects.get(latest, ""))


def upstream_summary(rows: list[tuple[str, str, str, str, str]]) -> str:
    informational = {"最新", "参考", "Buildroot 安定版待ち"}
    return "更新あり" if any(row[3] not in informational for row in rows) else "全て最新"


def branch_key(name: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", name))


def parse_latest_go_version(data: str) -> str:
    versions = []
    for release in json.loads(data):
        if not isinstance(release, dict) or release.get("stable") is not True:
            continue
        version = release.get("version", "")
        match = re.fullmatch(r"go(\d+\.\d+\.\d+)", version)
        if match:
            versions.append(match.group(1))
    return max(versions, key=branch_key) if versions else ""


def workflow_env(root: Path, workflow: str, key: str) -> str:
    text = (root / workflow).read_text()
    match = re.search(rf"^\s+{re.escape(key)}:\s*([^\s#]+)", text, re.M)
    return match.group(1) if match else ""


def docker_arg(root: Path, name: str) -> str:
    text = (root / "docker/msd-dev.Dockerfile").read_text()
    match = re.search(rf"^ARG {re.escape(name)}=([^\s#]+)\s*$", text, re.M)
    return match.group(1) if match else ""


def docker_image_pins(root: Path) -> dict[str, tuple[str, str]]:
    text = (root / "docker/msd-dev.Dockerfile").read_text()
    images: dict[str, tuple[str, str]] = {}
    for reference in re.findall(
        r"^FROM\s+(?:--platform=\S+\s+)?([^\s]+)", text, re.M
    ):
        image, _, digest = reference.partition("@")
        repository, separator, tag = image.rpartition(":")
        if separator:
            images[repository] = (tag, digest)
    return images


def go_builder_version(root: Path) -> str:
    tag = docker_image_pins(root).get("golang", ("", ""))[0]
    match = re.fullmatch(r"(\d+\.\d+\.\d+)-trixie", tag)
    return match.group(1) if match else ""


def workflow_checksum(text: str, archive_variable: str) -> str:
    marker = f'"${archive_variable}" | sha256sum -c -'
    before, separator, _ = text.partition(marker)
    if not separator:
        return ""
    checksums = re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", before)
    return checksums[-1] if checksums else ""


def parse_debian_package_versions(data: bytes) -> dict[str, str]:
    versions: dict[str, str] = {}
    for block in lzma.decompress(data).decode().split("\n\n"):
        fields = dict(
            line.split(": ", 1)
            for line in block.splitlines()
            if ": " in line
        )
        package = fields.get("Package", "")
        version = fields.get("Version", "")
        if package in {"qemu-system-arm", "qemu-utils"} and version:
            versions[package] = version
    return versions


def parse_qemu_latest(data: str) -> str:
    versions = re.findall(r"\bqemu-(\d+\.\d+\.\d+)\.tar\.xz\b", data)
    return max(versions, key=branch_key) if versions else ""


def debian_snapshot_status(snapshot: str, today: date | None = None) -> str:
    match = re.fullmatch(r"(\d{8})T\d{6}Z", snapshot)
    if not match:
        return "確認できず"
    snapshot_date = datetime.strptime(match.group(1), "%Y%m%d").date()
    current_date = today or date.today()
    return "更新あり" if (current_date - snapshot_date).days > 30 else "最新"


def run(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(
        args, cwd=cwd, text=True, stderr=subprocess.STDOUT, timeout=30
    )


def buildroot_gitlink_sha(root: Path) -> str:
    try:
        fields = run("git", "ls-tree", "HEAD", "vendor/buildroot", cwd=root).split()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""
    if len(fields) >= 3 and fields[0] == "160000" and fields[1] == "commit":
        return fields[2]
    return ""


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

    runners: set[str] = set()
    for path in sorted((root / ".github/workflows").glob("*.yml")):
        text = path.read_text()
        runners.update(
            re.findall(r"^\s*runs-on:\s*(ubuntu-\d+\.04(?:-arm)?)\s*$", text, re.M)
        )
        runners.update(
            re.findall(r"^\s*runner:\s*(ubuntu-\d+\.04(?:-arm)?)\s*$", text, re.M)
        )
    supported_runners = {"ubuntu-26.04", "ubuntu-26.04-arm"}
    if not runners or not runners.issubset(supported_runners):
        errors.append("workflow runs-on labels must use the current Ubuntu 26.04 images")
    actionlint = (root / ".github/actionlint.yaml").read_text()
    ignored = re.findall(r"label \"([^\"]+)\" is unknown", actionlint)
    if not runners.issubset(set(ignored)) or set(ignored) - runners:
        errors.append("actionlint ignored runner labels differ from workflows")

    readme = (root / "README.md").read_text()
    readme_version = re.search(r"\| ビルド \| Buildroot ([0-9.]+) \|", readme)
    branch = parse_buildroot_branch((root / ".gitmodules").read_text())
    if not readme_version or readme_version.group(1) != branch.removesuffix(".x"):
        errors.append("README Buildroot version differs from .gitmodules")

    buildroot_root = root / "vendor/buildroot"
    bootlin_config = (
        buildroot_root
        / "toolchain/toolchain-external/toolchain-external-bootlin/Config.in.options"
    )
    if (buildroot_root / ".git").exists() or bootlin_config.is_file():
        bootlin_option = selected_bootlin_option(definition)
        if not bootlin_option or not parse_bootlin_option_version(
            bootlin_config.read_text() if bootlin_config.is_file() else "",
            bootlin_option,
        ):
            errors.append(
                "defconfig Bootlin toolchain option must exist in "
                "Buildroot Config.in.options"
            )

    for workflow in (".github/workflows/lint.yml", ".github/workflows/build.yml"):
        text = (root / workflow).read_text()
        for name in ("ACTIONLINT_VERSION", "SHELLCHECK_VERSION"):
            if re.search(rf"\b{re.escape(name)}\b", text):
                errors.append(f"{workflow} must not contain {name}")
        if re.search(r"\bapt-get\s+install\b", text):
            errors.append(f"{workflow} must not install host packages with apt-get")
    for name in ("ACTIONLINT_VERSION", "SHELLCHECK_VERSION", "SHELLCHECK_SHA256"):
        if not docker_arg(root, name):
            errors.append(f"{name} must be set in docker/msd-dev.Dockerfile")
    for name, pattern in (
        ("QEMU_SHA256", r"[0-9a-f]{64}"),
        ("QEMU_SIGNING_FINGERPRINT", r"[0-9A-F]{40}"),
    ):
        if not re.fullmatch(pattern, docker_arg(root, name)):
            errors.append(f"{name} must be a valid hexadecimal pin")
    patch_directory = root / "docker/qemu-patches"
    patch_readme = patch_directory / "README.md"
    patch_names = [path.name for path in sorted(patch_directory.glob("*.patch"))]
    if not patch_readme.is_file():
        errors.append("docker/qemu-patches/README.md is missing")
    else:
        readme_text = patch_readme.read_text()
        for patch_name in patch_names:
            if patch_name not in readme_text:
                errors.append(f"{patch_name} is missing from docker/qemu-patches/README.md")
    base_images = docker_image_pins(root)
    if not go_builder_version(root):
        errors.append("Go builder image must use a versioned -trixie tag")
    for repository, description in (
        ("golang", "Go builder"),
        ("debian", "Debian runtime"),
    ):
        _, digest = base_images.get(repository, ("", ""))
        if not digest.startswith("sha256:"):
            errors.append(f"{description} image must be pinned by digest")
    for name in ("TRIVY_VERSION", "TRIVY_DIGEST"):
        workflow_values = [
            workflow_env(root, workflow, name)
            for workflow in (
                ".github/workflows/publish-dev-image.yml",
                ".github/workflows/dev-image-scan.yml",
            )
        ]
        if not workflow_values[0] or workflow_values[0] != workflow_values[1]:
            errors.append(f"{name} differs between development image workflows")
    return errors


def fetch(url: str) -> str:
    request = Request(url, headers={"Accept": "application/vnd.github+json"})
    if os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urlopen(request, timeout=20) as response:
        return response.read().decode()


def fetch_go_releases() -> str:
    request = Request(
        "https://go.dev/dl/?mode=json", headers={"Accept": "application/json"}
    )
    with urlopen(request, timeout=20) as response:
        return response.read().decode()


def fetch_qemu_releases() -> str:
    request = Request(
        "https://download.qemu.org/", headers={"Accept": "text/html"}
    )
    with urlopen(request, timeout=20) as response:
        return response.read().decode()


def fetch_dockerhub_digest(repository: str, tag: str) -> str:
    url = f"https://hub.docker.com/v2/repositories/library/{repository}/tags/{tag}"
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode())
    return str(data.get("digest") or "")


def upstream(report_path: Path, root: Path, today: date | None = None) -> int:
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
    buildroot_repo = "https://gitlab.com/buildroot.org/buildroot.git"
    buildroot_branches: list[str] = []
    buildroot_newest = "確認できず"
    try:
        refs = parse_ls_remote(run(
            "git",
            "ls-remote",
            "--heads",
            buildroot_repo,
            "refs/heads/20*.x",
        ))
        buildroot_branches = [
            name
            for name in refs
            if re.fullmatch(r"\d{4}\.\d{2}\.x", name)
        ]
        buildroot_newest = (
            max(buildroot_branches, key=branch_key)
            if buildroot_branches
            else "確認できず"
        )
        lts = [name for name in buildroot_branches if name.endswith(".02.x")]
        newest_lts = max(lts, key=branch_key) if lts else "確認できず"
        current = (
            branch_key(branch) >= branch_key(buildroot_newest)
            if buildroot_newest != "確認できず"
            else False
        )
        status = (
            "確認できず"
            if buildroot_newest == "確認できず"
            else ("最新" if current else "更新あり")
        )
        rows.append(("Buildroot", branch, buildroot_newest, status,
                     "https://gitlab.com/buildroot.org/buildroot/-/branches"))
        rows.append(("Buildroot LTS", branch, newest_lts, "参考",
                     "https://gitlab.com/buildroot.org/buildroot/-/branches"))
    except (OSError, URLError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        rows.append(("Buildroot", branch, "確認できず", "確認できず",
                     "https://gitlab.com/buildroot.org/buildroot/-/branches"))
        rows.append(("Buildroot LTS", branch, "確認できず", "参考",
                     "https://gitlab.com/buildroot.org/buildroot/-/branches"))

    bootlin_option = selected_bootlin_option(definition)
    bootlin_config = (
        root
        / "vendor/buildroot/toolchain/toolchain-external/"
        "toolchain-external-bootlin/Config.in.options"
    )
    try:
        bootlin_pinned = (
            parse_bootlin_option_version(bootlin_config.read_text(), bootlin_option)
            if bootlin_option and bootlin_config.is_file()
            else ""
        )
    except OSError:
        bootlin_pinned = ""
    bootlin_url = (
        "https://toolchains.bootlin.com/downloads/releases/toolchains/"
        "aarch64/tarballs/"
    )
    try:
        bootlin_latest = parse_bootlin_latest(fetch(bootlin_url))
        if not bootlin_latest:
            raise ValueError("no stable aarch64 glibc release found")
    except (OSError, URLError, ValueError) as exc:
        print(f"Bootlin toolchain: upstream check unavailable: {exc}", file=sys.stderr)
        bootlin_latest = ""

    bootlin_offered: str | None = None
    if bootlin_option and buildroot_newest != "確認できず":
        branch_url = (
            "https://gitlab.com/buildroot.org/buildroot/-/raw/"
            f"{buildroot_newest}/toolchain/toolchain-external/"
            "toolchain-external-bootlin/Config.in.options"
        )
        try:
            branch_config = fetch(branch_url)
            if not re.search(r"^config\s+[A-Za-z0-9_]+", branch_config, re.M):
                raise ValueError("invalid Buildroot Bootlin Kconfig")
            if bootlin_option_block(branch_config, bootlin_option) is None:
                bootlin_offered = ""
            else:
                bootlin_offered = (
                    parse_bootlin_option_version(branch_config, bootlin_option)
                    or None
                )
        except (OSError, URLError, ValueError) as exc:
            print(
                f"Bootlin Buildroot branch: upstream check unavailable: {exc}",
                file=sys.stderr,
            )
            bootlin_offered = None
    bootlin_latest_display, bootlin_state = bootlin_status(
        bootlin_pinned or "未設定",
        bootlin_latest,
        bootlin_offered,
        buildroot_newest,
    )
    rows.append(
        (
            "Bootlin toolchain (aarch64 glibc stable)",
            bootlin_pinned or "未設定",
            bootlin_latest_display,
            bootlin_state,
            "https://toolchains.bootlin.com/releases_aarch64.html",
        )
    )

    buildroot_gitlink = buildroot_gitlink_sha(root)
    buildroot_point_latest = "確認できず"
    buildroot_point_state = "確認できず"
    try:
        if not re.fullmatch(r"\d{4}\.\d{2}\.x", branch):
            raise ValueError("pinned Buildroot branch is not a stable series")
        tags = run(
            "git",
            "ls-remote",
            "--tags",
            buildroot_repo,
        )
        buildroot_point_latest, latest_commit = parse_buildroot_point_release(
            tags, branch
        )
        if not buildroot_point_latest or not latest_commit or not buildroot_gitlink:
            raise ValueError("Buildroot point release or gitlink is unavailable")
        buildroot_point_state = (
            "最新" if buildroot_gitlink == latest_commit else "参考"
        )
    except (
        OSError,
        URLError,
        ValueError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as exc:
        buildroot_point_latest = "確認できず"
        buildroot_point_state = "確認できず"
        print(
            f"Buildroot point release: upstream check unavailable: {exc}",
            file=sys.stderr,
        )
    rows.append(
        (
            "Buildroot point release",
            buildroot_gitlink or "未設定",
            buildroot_point_latest,
            buildroot_point_state,
            "https://gitlab.com/buildroot.org/buildroot/-/tags",
        )
    )

    for name, repository, env_name, workflow in (
        ("actionlint", "rhysd/actionlint", "ACTIONLINT_VERSION", ""),
        ("ShellCheck", "koalaman/shellcheck", "SHELLCHECK_VERSION", ""),
        ("hadolint", "hadolint/hadolint", "HADOLINT_VERSION", ".github/workflows/lint.yml"),
        (
            "kernel-hardening-checker",
            "a13xp0p0v/kernel-hardening-checker",
            "KHC_TAG",
            ".github/workflows/build.yml",
        ),
    ):
        pin = os.environ.get(env_name) or (
            docker_arg(root, env_name)
            if not workflow
            else workflow_env(root, workflow, env_name)
        ) or "未設定"
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

    qemu_pin = docker_arg(root, "QEMU_VERSION") or "未設定"
    qemu_url = "https://download.qemu.org/"
    try:
        latest_qemu = parse_qemu_latest(fetch_qemu_releases())
        qemu_status = (
            "確認できず"
            if not latest_qemu
            else "最新"
            if qemu_pin == latest_qemu
            else "更新あり"
        )
    except (OSError, URLError, ValueError) as exc:
        print(f"QEMU: upstream check unavailable: {exc}", file=sys.stderr)
        latest_qemu, qemu_status = "確認できず", "確認できず"
    rows.append(("QEMU", qemu_pin, latest_qemu or "確認できず", qemu_status, qemu_url))
    snapshot = docker_arg(root, "DEBIAN_SNAPSHOT") or "未設定"
    rows.append(
        (
            "Debian snapshot date",
            snapshot,
            "-",
            debian_snapshot_status(snapshot, today),
            "https://snapshot.debian.org/",
        )
    )

    trivy_pin = (
        workflow_env(root, ".github/workflows/publish-dev-image.yml", "TRIVY_VERSION")
        or "未設定"
    )
    trivy_url = "https://github.com/aquasecurity/trivy/releases"
    try:
        latest_trivy = parse_release(
            fetch("https://api.github.com/repos/aquasecurity/trivy/releases/latest")
        )
        trivy_status = (
            "最新"
            if trivy_pin.lstrip("v") == latest_trivy.lstrip("v")
            else "更新あり"
        )
    except (OSError, URLError, ValueError) as exc:
        print(f"Trivy: upstream check unavailable: {exc}", file=sys.stderr)
        latest_trivy, trivy_status = "確認できず", "確認できず"
    rows.append(("Trivy", trivy_pin, latest_trivy, trivy_status, trivy_url))

    go_pin = go_builder_version(root) or "未設定"
    try:
        latest_go = parse_latest_go_version(fetch_go_releases())
        if not latest_go:
            go_status = "確認できず"
        else:
            go_status = "最新" if go_pin == latest_go else "更新あり"
    except (OSError, URLError, ValueError) as exc:
        print(f"Go: upstream check unavailable: {exc}", file=sys.stderr)
        latest_go, go_status = "確認できず", "確認できず"
    rows.append(
        (
            "Go toolchain",
            go_pin,
            latest_go or "確認できず",
            go_status,
            "https://go.dev/dl/",
        )
    )

    base_images = docker_image_pins(root)
    for repository, name in (
        ("golang", "Go builder image digest"),
        ("debian", "Debian base image digest"),
    ):
        tag, pinned_digest = base_images.get(repository, ("", ""))
        source = f"https://hub.docker.com/_/{repository}?tab=tags&name={tag}"
        try:
            latest_digest = fetch_dockerhub_digest(repository, tag) if tag else ""
            if not latest_digest:
                digest_status = "確認できず"
            else:
                digest_status = (
                    "最新" if pinned_digest == latest_digest else "更新あり"
                )
        except (OSError, URLError, ValueError) as exc:
            print(f"{name}: upstream check unavailable: {exc}", file=sys.stderr)
            latest_digest, digest_status = "", "確認できず"
        rows.append(
            (
                name,
                pinned_digest or "未設定",
                latest_digest or "確認できず",
                digest_status,
                source,
            )
        )

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
    lines = [
             "| 依存 | 固定値 | 最新 | 状態(最新・更新あり・確認できず・参考・Buildroot 安定版待ち) | 参照URL |",
             "|---|---|---|---|---|"]
    lines.extend(f"| {name} | `{pin}` | `{latest}` | {status} | {url} |"
                 for name, pin, latest, status, url in rows)
    report_path.write_text("\n".join(lines) + "\n")
    print(upstream_summary(rows))
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
