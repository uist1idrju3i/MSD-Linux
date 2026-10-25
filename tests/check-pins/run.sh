#!/bin/sh
set -eu

repo_root="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"

python3 - "$repo_root" <<'PY'
import contextlib
import importlib.util
import io
import json
import pathlib
import shutil
import sys
import tempfile
from datetime import date

root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("check_pins", root / ".github/scripts/check-pins.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

sha = "234188315037848e5b07d65b85d38edc64095caa"
fixtures = []


def fixture() -> pathlib.Path:
    path = pathlib.Path(tempfile.mkdtemp())
    fixtures.append(path)
    (path / "configs").mkdir()
    (path / "board/cardputerzero/patches/linux").mkdir(parents=True)
    (path / "package/m5stack-cardputerzero").mkdir(parents=True)
    (path / ".github/workflows").mkdir(parents=True)
    (path / "docker/qemu-patches").mkdir(parents=True)
    buildroot_config = (
        path
        / "vendor/buildroot/toolchain/toolchain-external/"
        "toolchain-external-bootlin/Config.in.options"
    )
    buildroot_config.parent.mkdir(parents=True)
    buildroot_config.write_text(
        'config BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_AARCH64_GLIBC_STABLE\n'
        '  bool "aarch64 glibc stable 2025.08-1"\n'
        '  depends on BR2_aarch64\n'
    )
    (path / "configs/msd_cardputerzero_defconfig").write_text(
        f'BR2_LINUX_KERNEL_CUSTOM_TARBALL_LOCATION="linux-{sha}.tar.gz"\n'
        f'BR2_LINUX_KERNEL_CUSTOM_TARBALL_LOCATION="linux-{sha}.tar.gz"\n'
        'BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_AARCH64_GLIBC_STABLE=y\n'
    )
    (path / "board/cardputerzero/patches/linux/linux.hash").write_text(
        f"sha256 deadbeef linux-{sha}.tar.gz\n"
    )
    (path / "package/m5stack-cardputerzero/m5stack-cardputerzero.mk").write_text(
        "M5STACK_CARDPUTERZERO_VERSION := $(shell git -C $(M5STACK_CARDPUTERZERO_SITE) rev-parse HEAD)\n"
    )
    (path / ".github/workflows/lint.yml").write_text(
        "env:\n"
        "  HADOLINT_VERSION: 2.15.1\n"
        "jobs:\n  lint:\n    runs-on: ubuntu-26.04\n"
    )
    (path / ".github/workflows/publish-dev-image.yml").write_text(
        "env:\n"
        "  TRIVY_VERSION: 0.76.0\n"
        "  TRIVY_DIGEST: sha256:" + "1" * 64 + "\n"
        "jobs:\n  build:\n    strategy:\n      matrix:\n"
        "        include:\n          - arch: amd64\n"
        "            runner: ubuntu-26.04\n"
        "          - arch: arm64\n"
        "            runner: ubuntu-26.04-arm\n"
    )
    (path / ".github/workflows/dev-image-scan.yml").write_text(
        "env:\n"
        "  TRIVY_VERSION: 0.76.0\n"
        "  TRIVY_DIGEST: sha256:" + "1" * 64 + "\n"
        "jobs:\n  scan:\n    runs-on: ubuntu-26.04\n"
    )
    (path / "docker/msd-dev.Dockerfile").write_text(
        "ARG ACTIONLINT_VERSION=1.7.12\n"
        "ARG DEBIAN_SNAPSHOT=20261019T190000Z\n"
        "ARG QEMU_VERSION=11.1.2\n"
        "ARG QEMU_SHA256=" + "1" * 64 + "\n"
        "ARG QEMU_SIGNING_FINGERPRINT=CEACC9E15534EBABB82D3FA03353C9CEF108B584\n"
        "FROM golang:1.27.2-trixie@sha256:" + "c" * 64 + " AS actionlint\n"
        "ARG ACTIONLINT_VERSION\n"
        "FROM debian:trixie-slim@sha256:" + "b" * 64 + " AS msd-dev\n"
        "ARG ACTIONLINT_VERSION\n"
        "ARG DEBIAN_SNAPSHOT=20261019T190000Z\n"
        "ARG SHELLCHECK_VERSION=0.11.0\n"
        "ARG SHELLCHECK_SHA256=8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198\n"
    )
    (path / "docker/qemu-patches/README.md").write_text(
        "`0001-hw-arm-bcm2835_peripherals-add-unimp-ASB.patch`\n"
    )
    (path / "docker/qemu-patches/0001-hw-arm-bcm2835_peripherals-add-unimp-ASB.patch").write_text(
        "fixture patch\n"
    )
    (path / ".github/workflows/build.yml").write_text(
        "env:\n"
        "  KHC_TAG: v0.6.17.1\n"
        "  KHC_COMMIT: afc376f2a935994793343cfeb05953583cc30191\n"
        "jobs:\n  build:\n    runs-on: ubuntu-26.04\n"
    )
    (path / ".github/actionlint.yaml").write_text(
        'paths:\n  .github/workflows/*.yml:\n    ignore:\n'
        '      - \'label "ubuntu-26.04" is unknown\'\n'
        '      - \'label "ubuntu-26.04-arm" is unknown\'\n'
    )
    (path / ".gitmodules").write_text(
        '[submodule "vendor/buildroot"]\n\tpath = vendor/buildroot\n\turl = https://example.test/buildroot\n\tbranch = 2026.08.x\n'
    )
    (path / "README.md").write_text("| ビルド | Buildroot 2026.08 |\n")
    return path


passed = fixture()
errors = module.consistency(passed)
assert errors == [], errors
print("ok - consistency accepts a matching fixture")

for workflow, line, expected in (
    (".github/workflows/lint.yml", "ACTIONLINT_VERSION: 1.7.12", "ACTIONLINT_VERSION"),
    (".github/workflows/build.yml", "SHELLCHECK_VERSION: 0.11.0", "SHELLCHECK_VERSION"),
    (".github/workflows/lint.yml", "sudo apt-get install shellcheck", "apt-get"),
    (".github/workflows/build.yml", "sudo apt-get install qemu-system-arm", "apt-get"),
):
    bad_workflow = fixture()
    path = bad_workflow / workflow
    path.write_text(path.read_text() + "\n" + line + "\n")
    assert any(expected in error for error in module.consistency(bad_workflow))
print("ok - rejects duplicate lint pins and host apt installs")

bad_docker_tool_pin = fixture()
dockerfile = bad_docker_tool_pin / "docker/msd-dev.Dockerfile"
dockerfile.write_text(dockerfile.read_text().replace(
    "ARG ACTIONLINT_VERSION=1.7.12",
    "ARG ACTIONLINT_VERSION=1.7.11",
))
assert module.consistency(bad_docker_tool_pin) == []
print("ok - Dockerfile is the sole actionlint version source")

for name, value in (
    ("ACTIONLINT_VERSION", "1.7.12"),
    ("SHELLCHECK_VERSION", "0.11.0"),
    ("SHELLCHECK_SHA256", "8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198"),
):
    missing_docker_pin = fixture()
    dockerfile = missing_docker_pin / "docker/msd-dev.Dockerfile"
    dockerfile.write_text(
        dockerfile.read_text().replace(f"ARG {name}={value}\n", "")
    )
    assert any(
        name in error for error in module.consistency(missing_docker_pin)
    )
print("ok - Dockerfile lint pins are required")

bad_docker_hash = fixture()
dockerfile = bad_docker_hash / "docker/msd-dev.Dockerfile"
dockerfile.write_text(dockerfile.read_text().replace(
    "ARG SHELLCHECK_SHA256=8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198",
    "ARG SHELLCHECK_SHA256=" + "0" * 64,
))
assert module.consistency(bad_docker_hash) == []
print("ok - consistency does not duplicate the ShellCheck checksum")

bad_qemu_sha = fixture()
dockerfile = bad_qemu_sha / "docker/msd-dev.Dockerfile"
dockerfile.write_text(dockerfile.read_text().replace(
    "ARG QEMU_SHA256=" + "1" * 64,
    "ARG QEMU_SHA256=" + "z" * 64,
))
assert any("QEMU_SHA256" in error for error in module.consistency(bad_qemu_sha))
print("ok - detects an invalid QEMU checksum")

bad_qemu_fingerprint = fixture()
dockerfile = bad_qemu_fingerprint / "docker/msd-dev.Dockerfile"
dockerfile.write_text(dockerfile.read_text().replace(
    "CEACC9E15534EBABB82D3FA03353C9CEF108B584",
    "CEACC9E15534EBABB82D3FA03353C9CEF108B58",
))
assert any("QEMU_SIGNING_FINGERPRINT" in error for error in module.consistency(bad_qemu_fingerprint))
print("ok - detects an invalid QEMU signing fingerprint")

bad_qemu_patch_readme = fixture()
(bad_qemu_patch_readme / "docker/qemu-patches/README.md").write_text("")
assert any("missing from docker/qemu-patches/README.md" in error
           for error in module.consistency(bad_qemu_patch_readme))
print("ok - requires every QEMU patch in its README")

bad_trivy_version = fixture()
publish_workflow = bad_trivy_version / ".github/workflows/publish-dev-image.yml"
publish_workflow.write_text(publish_workflow.read_text().replace(
    "TRIVY_VERSION: 0.76.0",
    "TRIVY_VERSION: 0.75.0",
))
assert any("TRIVY_VERSION" in error for error in module.consistency(bad_trivy_version))
print("ok - detects Trivy version drift between workflows")

bad_trivy_digest = fixture()
scan_workflow = bad_trivy_digest / ".github/workflows/dev-image-scan.yml"
scan_workflow.write_text(scan_workflow.read_text().replace(
    "TRIVY_DIGEST: sha256:" + "1" * 64,
    "TRIVY_DIGEST: sha256:" + "2" * 64,
))
assert any("TRIVY_DIGEST" in error for error in module.consistency(bad_trivy_digest))
print("ok - detects Trivy image digest drift between workflows")

bad_hash = fixture()
(bad_hash / "board/cardputerzero/patches/linux/linux.hash").write_text(
    "sha256 deadbeef linux-" + "0" * 40 + ".tar.gz\n"
)
assert any("linux.hash" in error for error in module.consistency(bad_hash))
print("ok - detects a mismatched linux.hash")

bad_bootlin_option = fixture()
bootlin_config = (
    bad_bootlin_option
    / "vendor/buildroot/toolchain/toolchain-external/"
    "toolchain-external-bootlin/Config.in.options"
)
bootlin_config.write_text(
    'config BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_X86_GLIBC_STABLE\n'
    '  bool "x86 glibc stable 2025.08-1"\n'
)
assert any("Bootlin" in error for error in module.consistency(bad_bootlin_option))
print("ok - detects a missing Bootlin option in checked-out Buildroot")

bad_runner = fixture()
(bad_runner / ".github/workflows/build.yml").write_text("jobs:\n  build:\n    runs-on: ubuntu-24.04\n")
assert any("runs-on" in error for error in module.consistency(bad_runner))
print("ok - detects differing runner labels")

bad_readme = fixture()
(bad_readme / "README.md").write_text("| ビルド | Buildroot 2026.02 |\n")
assert any("README" in error for error in module.consistency(bad_readme))
print("ok - detects a README Buildroot mismatch")

bad_make = fixture()
makefile = bad_make / "package/m5stack-cardputerzero/m5stack-cardputerzero.mk"
makefile.write_text(makefile.read_text() + "\n" + "a" * 40 + "\n")
assert any("literal SHA" in error for error in module.consistency(bad_make))
print("ok - detects a hardcoded package SHA")

assert module.parse_ls_remote(f"{sha}\trefs/heads/rpi-6.18.y\n") == {"rpi-6.18.y": sha}
assert module.parse_buildroot_branch(
    '[submodule "vendor/buildroot"]\n path = vendor/buildroot\n url = x\n branch = 2026.08.x\n'
) == "2026.08.x"
assert module.parse_release('{"tag_name":"v1.2.3"}') == "v1.2.3"
quoted_env = fixture()
(quoted_env / ".github/workflows/publish-dev-image.yml").write_text(
    "env:\n  TRIVY_VERSION: \"0.76.0\"\n  OTHER: 'v1'\n  PLAIN: 2.0\n"
)
assert module.workflow_env(quoted_env, ".github/workflows/publish-dev-image.yml", "TRIVY_VERSION") == "0.76.0"
assert module.workflow_env(quoted_env, ".github/workflows/publish-dev-image.yml", "OTHER") == "v1"
assert module.workflow_env(quoted_env, ".github/workflows/publish-dev-image.yml", "PLAIN") == "2.0"
assert module.parse_latest_go_version(
    json.dumps(
        [
            {"version": "go1.27.1", "stable": True},
            {"version": "go1.26.9", "stable": True},
            {"version": "go1.27.2", "stable": True},
            {"version": "go1.26.10rc1", "stable": False},
        ]
    )
) == "1.27.2"
assert module.parse_qemu_latest(
    '<a href="qemu-11.0.0.tar.xz">11.0.0</a>'
    '<a href="qemu-11.1.2.tar.xz">11.1.2</a>'
    '<a href="qemu-12.0.0-rc1.tar.xz">12.0.0-rc1</a>'
) == "11.1.2"
bootlin_option = "BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_AARCH64_GLIBC_STABLE"
bootlin_config = (
    f"config {bootlin_option}\n"
    '  bool "aarch64 glibc stable 2025.08-1"\n'
    "  depends on BR2_aarch64\n"
    "config BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_AARCH64_MUSL_STABLE\n"
    '  bool "aarch64 musl stable 2025.08-1"\n'
)
assert module.parse_bootlin_option_version(bootlin_config, bootlin_option) == "2025.08-1"
assert module.parse_bootlin_option_version(
    bootlin_config, "BR2_TOOLCHAIN_EXTERNAL_MISSING"
) == ""
assert module.parse_bootlin_latest(
    '<a href="aarch64--glibc--stable-2025.08-1.tar.xz">2025.08-1</a>'
    '<a href="aarch64--glibc--stable-2026.08-1.tar.xz">2026.08-1</a>'
    '<a href="aarch64--glibc--stable-2027.02-1-rc1.tar.xz">release candidate</a>'
) == "2026.08-1"
assert module.parse_bootlin_latest("<html>no toolchain archives</html>") == ""
assert module.bootlin_status(
    "2025.08-1", "2025.08-1", "2025.08-1", "2026.08.x"
) == ("2025.08-1", "最新")
assert module.bootlin_status(
    "2025.08-1", "2026.08-1", "", "2026.08.x"
) == (
    "2026.08-1（安定版の Buildroot では未提供）",
    "Buildroot 安定版待ち",
)
assert module.bootlin_status(
    "2025.08-1", "2026.08-1", "2026.08-1", "2026.11.x"
) == (
    "2026.08-1（Buildroot 2026.11.x で選択可）",
    "更新あり",
)
assert module.bootlin_status(
    "2025.08-1", "", "2026.08-1", "2026.11.x"
) == ("確認できず", "確認できず")
assert module.bootlin_status(
    "2025.08-1", "2026.08-1", None, "2026.11.x"
) == ("2026.08-1", "確認できず")
assert module.upstream_summary(
    [("Bootlin", "2025.08-1", "2026.08-1", "Buildroot 安定版待ち", "")]
) == "全て最新"
assert module.parse_buildroot_point_release(
    f"{'a' * 40}\trefs/tags/2026.08.2\n"
    f"{'b' * 40}\trefs/tags/2026.08.2^{{}}\n"
    f"{'c' * 40}\trefs/tags/2026.08.3\n"
    f"{'d' * 40}\trefs/tags/2026.08.3^{{}}\n"
    f"{'e' * 40}\trefs/tags/2026.11.1^{{}}\n",
    "2026.08.x",
) == ("2026.08.3", "d" * 40)
assert module.parse_buildroot_point_release(
    f"{'a' * 40}\trefs/tags/2026.08\n"
    f"{'b' * 40}\trefs/tags/2026.08^{{}}\n"
    f"{'c' * 40}\trefs/tags/2026.08-rc3\n",
    "2026.08.x",
) == ("2026.08", "b" * 40)
assert module.parse_buildroot_point_release(
    f"{'a' * 40}\trefs/tags/2026.08\n"
    f"{'b' * 40}\trefs/tags/2026.08^{{}}\n"
    f"{'c' * 40}\trefs/tags/2026.08.1\n"
    f"{'d' * 40}\trefs/tags/2026.08.1^{{}}\n",
    "2026.08.x",
) == ("2026.08.1", "d" * 40)
assert module.parse_buildroot_point_release("", "2026.08.x") == ("", "")
assert module.parse_runner_labels("| `ubuntu-24.04` | beta image |\n") == [
    ("ubuntu-24.04", "beta")
]
print("ok - parses ls-remote, .gitmodules, releases, and runner README data")
print("ok - parses Bootlin options/releases and Buildroot point tags")
print("ok - classifies Bootlin stable-toolchain availability")
print("ok - treats Buildroot stable-wait status as non-actionable")

run_calls = []


def fake_run(*args, cwd=None):
    run_calls.append(args)
    if "ls-tree" in args:
        return f"160000 commit {sha}\tvendor/buildroot\n"
    if "--tags" in args:
        return (
            f"{'c' * 40}\trefs/tags/2026.08.2\n"
            f"{'d' * 40}\trefs/tags/2026.08.2^{{}}\n"
            f"{'e' * 40}\trefs/tags/2026.08.3\n"
            f"{'f' * 40}\trefs/tags/2026.08.3^{{}}\n"
            f"{'1' * 40}\trefs/tags/2026.11.1^{{}}\n"
        )
    if any("raspberrypi/linux.git" in arg for arg in args):
        return (
            f"{sha}\trefs/heads/rpi-6.18.y\n"
            f"{'a' * 40}\trefs/heads/rpi-7.3.y\n"
        )
    return (
        f"{'b' * 40}\trefs/heads/2026.08.x\n"
        f"{'c' * 40}\trefs/heads/2026.02.x\n"
        f"{'d' * 40}\trefs/heads/master\n"
    )


def fake_run_without_point_tags(*args, cwd=None):
    if "--tags" in args:
        return ""
    return fake_run(*args, cwd=cwd)


fetch_calls = []


def fake_fetch(url):
    fetch_calls.append(url)
    if "toolchains.bootlin.com/downloads/releases/toolchains/aarch64/tarballs" in url:
        return (
            '<a href="aarch64--glibc--stable-2025.08-1.tar.xz">2025.08-1</a>'
            '<a href="aarch64--glibc--stable-2026.08-1.tar.xz">2026.08-1</a>'
        )
    if "/-/raw/" in url and url.endswith("toolchain-external-bootlin/Config.in.options"):
        return (
            "config BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_AARCH64_GLIBC_STABLE\n"
            '  bool "aarch64 glibc stable 2025.08-1"\n'
        )
    if "rhysd/actionlint" in url:
        return '{"tag_name":"1.7.12"}'
    if "koalaman/shellcheck" in url:
        return '{"tag_name":"0.11.0"}'
    if "hadolint/hadolint" in url:
        return '{"tag_name":"v2.15.1"}'
    if "kernel-hardening-checker" in url:
        return '{"tag_name":"v0.6.17.1"}'
    if "aquasecurity/trivy" in url:
        return '{"tag_name":"v0.76.0"}'
    return "| `ubuntu-26.04` | current image |\n"


def fake_fetch_go_releases():
    return json.dumps(
        [
            {"version": "go1.27.1", "stable": True},
            {"version": "go1.26.9", "stable": True},
            {"version": "go1.27.2", "stable": True},
            {"version": "go1.26.10rc1", "stable": False},
        ]
    )


def fake_fetch_qemu_releases():
    return (
        '<a href="qemu-11.0.0.tar.xz">11.0.0</a>'
        '<a href="qemu-11.1.2.tar.xz">11.1.2</a>'
        '<a href="qemu-12.0.0-rc1.tar.xz">12.0.0-rc1</a>'
    )


def fake_fetch_dockerhub_digest(repository, tag):
    if repository == "golang" and tag == "1.27.2-trixie":
        return "sha256:" + "c" * 64
    if repository == "debian" and tag == "trixie-slim":
        return "sha256:" + "b" * 64
    return ""


module.run = fake_run
module.fetch = fake_fetch
module.fetch_go_releases = fake_fetch_go_releases
module.fetch_qemu_releases = fake_fetch_qemu_releases
module.fetch_dockerhub_digest = fake_fetch_dockerhub_digest
module.fetch_qemu_releases = lambda: "<html>no release tarballs</html>"
with tempfile.TemporaryDirectory() as directory:
    report_path = pathlib.Path(directory) / "pins.md"
    with contextlib.redirect_stdout(io.StringIO()):
        assert module.upstream(report_path, passed, today=date(2026, 10, 19)) == 0
    report = report_path.read_text()
    assert "| actionlint | `1.7.12` | `1.7.12` | 最新 |" in report
    assert "| ShellCheck | `0.11.0` | `0.11.0` | 最新 |" in report
    assert (
        "| QEMU | `11.1.2` | `確認できず` | 確認できず |"
        in report
    )
print("ok - reports a malformed QEMU release listing as unknown")

module.fetch_qemu_releases = fake_fetch_qemu_releases
with tempfile.TemporaryDirectory() as directory:
    report_path = pathlib.Path(directory) / "pins.md"
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert module.upstream(report_path, passed, today=date(2026, 10, 19)) == 0
    report = report_path.read_text()
    assert (
        "| Raspberry Pi Linux series | `rpi-6.18.y` | `rpi-7.3.y` | 参考 |"
        in report
    )
    assert "| QEMU | `11.1.2` | `11.1.2` | 最新 |" in report
    assert "| Trivy | `0.76.0` | `v0.76.0` | 最新 |" in report
    assert "| Go toolchain | `1.27.2` | `1.27.2` | 最新 |" in report
    assert (
        "| Go builder image digest | `sha256:" + "c" * 64 + "` | `sha256:"
        + "c" * 64 + "` | 最新 |"
    ) in report
    assert (
        "| Debian base image digest | `sha256:" + "b" * 64 + "` | `sha256:"
        + "b" * 64 + "` | 最新 |"
    ) in report
    assert "| Debian snapshot date | `20261019T190000Z` | `-` | 最新 |" in report
    assert "| Buildroot LTS | `2026.08.x` | `2026.02.x` | 参考 |" in report
    assert (
        "| Bootlin toolchain (aarch64 glibc stable) | `2025.08-1` | "
        "`2026.08-1（安定版の Buildroot では未提供）` | Buildroot 安定版待ち |"
        in report
    )
    assert (
        "| Buildroot point release | `" + sha + "` | `2026.08.3` | 参考 |"
        in report
    )
    assert any(args[-1] == "refs/heads/20*.x" for args in run_calls)
    assert any("/2026.08.x/" in url for url in fetch_calls)
    assert not any("/master/" in url for url in fetch_calls)
    assert output.getvalue().strip() == "全て最新"
print("ok - marks informational upstream rows as 参考 and excludes them from status")

qemu_update = fixture()
dockerfile = qemu_update / "docker/msd-dev.Dockerfile"
dockerfile.write_text(dockerfile.read_text().replace(
    "ARG QEMU_VERSION=11.1.2",
    "ARG QEMU_VERSION=11.0.2",
))
with tempfile.TemporaryDirectory() as directory:
    report_path = pathlib.Path(directory) / "pins.md"
    with contextlib.redirect_stdout(io.StringIO()):
        assert module.upstream(report_path, qemu_update, today=date(2026, 10, 19)) == 0
    assert "| QEMU | `11.0.2` | `11.1.2` | 更新あり |" in report_path.read_text()
print("ok - reports a newer QEMU source release as an update")

module.run = fake_run_without_point_tags
with tempfile.TemporaryDirectory() as directory:
    report_path = pathlib.Path(directory) / "pins.md"
    with contextlib.redirect_stdout(io.StringIO()):
        assert module.upstream(report_path, passed, today=date(2026, 10, 19)) == 0
    report = report_path.read_text()
    assert (
        "| Buildroot point release | `" + sha + "` | `確認できず` | 確認できず |"
        in report
    )
module.run = fake_run
print("ok - reports an unavailable Buildroot point release as unknown")

with tempfile.TemporaryDirectory() as directory:
    report_path = pathlib.Path(directory) / "pins.md"
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert module.upstream(report_path, passed, today=date(2026, 11, 19)) == 0
    report = report_path.read_text()
    assert "| Debian snapshot date | `20261019T190000Z` | `-` | 更新あり |" in report
    assert output.getvalue().strip() == "更新あり"
print("ok - reports snapshots older than 30 days as update candidates")

for path in fixtures:
    shutil.rmtree(path)
PY

issue_pattern='^([|]---.*|[|] 依存 [|].*|[|].*[|] (最新|参考|Buildroot 安定版待ち) [|].*[|])$'
reference_report='| 依存 | 固定値 | 最新 | 状態 | 参照URL |
|---|---|---|---|---|
| Raspberry Pi Linux series | rpi-6.18.y | rpi-7.3.y | 参考 | https://example.test |
| Buildroot LTS | 2026.08.x | 2026.02.x | 参考 | https://example.test |
| Bootlin toolchain (aarch64 glibc stable) | 2025.08-1 | 2026.08-1 | Buildroot 安定版待ち | https://example.test |'
if printf '%s\n' "$reference_report" | grep -qvE "$issue_pattern"; then
    echo "fail - informational rows must not trigger an issue" >&2
    exit 1
fi
echo "ok - ignores informational rows when deciding whether to open or update the issue"

actionable_report="$reference_report
| Raspberry Pi Linux | 234188315037848e5b07d65b85d38edc64095caa | 5d64d1ea73716526ed9c0ed184a9cb5f6042e32c | 更新あり | https://example.test |"
if ! printf '%s\n' "$actionable_report" | grep -qvE "$issue_pattern"; then
    echo "fail - update rows must trigger an issue" >&2
    exit 1
fi
actionable_report="$reference_report
| actionlint | 1.7.12 | 確認できず | 確認できず | https://example.test |"
if ! printf '%s\n' "$actionable_report" | grep -qvE "$issue_pattern"; then
    echo "fail - unknown rows must trigger an issue" >&2
    exit 1
fi
echo "ok - triggers an issue for update or unknown rows"
