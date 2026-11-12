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
from unittest.mock import patch
from urllib.request import HTTPRedirectHandler

root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("check_pins", root / ".github/scripts/check-pins.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

requests = []


def capture_request(request, timeout):
    assert timeout == 20
    requests.append(request)
    return io.BytesIO(b"fixture")


with patch.dict(module.os.environ, {"GITHUB_TOKEN": "fixture-token"}):
    with patch.object(module, "urlopen", capture_request):
        for url, authenticated in (
            ("https://api.github.com/repos/example/project/releases/latest", True),
            ("https://api.github.com:443/repos/example/project/releases/latest", True),
            ("https://toolchains.bootlin.com/downloads/releases/toolchains/", False),
            ("https://gitlab.com/buildroot.org/buildroot/-/raw/main/file", False),
            ("https://raw.githubusercontent.com/actions/runner-images/main/README.md", False),
            ("http://api.github.com/repos/example/project/releases/latest", False),
            ("https://api.github.com:8443/repos/example/project/releases/latest", False),
            ("https://api.github.com.example.test/releases/latest", False),
            ("https://api.github.com@example.test/releases/latest", False),
            ("https://example.test@api.github.com/releases/latest", False),
        ):
            assert module.fetch(url) == "fixture"
            request = requests[-1]
            assert request.get_header("Authorization") == (
                "Bearer fixture-token" if authenticated else None
            ), url
            for code in (301, 302, 303, 307, 308):
                for destination in (
                    "https://example.test/redirected",
                    "http://api.github.com/redirected",
                    "https://api.github.com/redirected",
                ):
                    redirected = HTTPRedirectHandler().redirect_request(
                        request, None, code, "redirect", {}, destination
                    )
                    assert redirected.get_header("Authorization") is None
print("ok - GitHub credentials are restricted to the HTTPS API and never redirected")

with patch.dict(module.os.environ, {"GITHUB_TOKEN": ""}):
    with patch.object(module, "urlopen", capture_request):
        assert module.fetch("https://api.github.com/repos/example/project") == "fixture"
        assert requests[-1].get_header("Authorization") is None
print("ok - unauthenticated GitHub requests remain supported")

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
        "ARG DEBIAN_SNAPSHOT=20261103T023120Z\n"
        "ARG QEMU_VERSION=11.1.2\n"
        "ARG QEMU_SHA256=" + "1" * 64 + "\n"
        "ARG QEMU_SIGNING_FINGERPRINT=CEACC9E15534EBABB82D3FA03353C9CEF108B584\n"
        "FROM golang:1.27.2-trixie@sha256:" + "c" * 64 + " AS actionlint\n"
        "ARG ACTIONLINT_VERSION\n"
        "FROM debian:trixie-slim@sha256:" + "b" * 64 + " AS msd-dev\n"
        "ARG ACTIONLINT_VERSION\n"
        "ARG DEBIAN_SNAPSHOT=20261103T023120Z\n"
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
version_calls = []


def github_versions(url):
    version_calls.append(url)
    if url.endswith("&page=1"):
        return json.dumps([{"tag_name": "v2.0.0"}] * 100)
    return json.dumps([
        {"tag_name": "v1.99.0"},
        {"tag_name": "v10.0.0"},
        {"tag_name": "v11.0.0", "draft": True},
        {"tag_name": "v12.0.0", "prerelease": True},
        {"tag_name": "v99.0.0-rc1"},
        {"tag_name": None},
    ])


with patch.object(module, "fetch", github_versions):
    assert module.latest_github_version("example/tool") == "v10.0.0"
assert version_calls == [
    "https://api.github.com/repos/example/tool/releases?per_page=100&page=1",
    "https://api.github.com/repos/example/tool/releases?per_page=100&page=2",
]
with patch.object(module, "fetch", return_value=json.dumps([
    {"name": "v0.6.9"}, {"name": "v0.6.17.1"}, {"name": "v0.7.0-rc1"},
])) as fetch_tags:
    assert module.latest_github_version("example/tool", tags=True) == "v0.6.17.1"
    assert "/tags?" in fetch_tags.call_args.args[0]
for response in ('[]', '{}', '[1]', '[{"tag_name":"nightly"}]'):
    with patch.object(module, "fetch", return_value=response):
        try:
            module.latest_github_version("example/tool")
        except ValueError:
            pass
        else:
            raise AssertionError("invalid or empty versions must remain unknown")
with patch.object(module, "fetch", return_value=json.dumps([{"tag_name": "v1.0"}] * 100)):
    try:
        module.latest_github_version("example/tool")
    except ValueError as error:
        assert "pagination limit" in str(error)
    else:
        raise AssertionError("truncated pagination must not produce a latest version")
print("ok - selects numeric stable versions across pages and majors, including tag-only projects")
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
        f"{'e' * 40}\trefs/heads/2025.02.x\n"
        f"{'d' * 40}\trefs/heads/master\n"
    )


def fake_run_without_point_tags(*args, cwd=None):
    if "--tags" in args:
        return ""
    return fake_run(*args, cwd=cwd)


fetch_calls = []


def openssl_table(rows):
    return (
        '<table><tr><th>Series</th><th>Filename</th><th>Size</th>'
        '<th>Release</th><th>End-of-Life</th><th>Checksums</th></tr>'
        + ''.join(
            f'<tr><td>{series}</td><td><a>{version}</a></td><td>50MiB</td>'
            f'<td>01 Oct 2026</td><td>{expiry}</td><td>SHA256</td></tr>'
            for series, version, expiry in rows
        ) + '</table>'
    )


def fake_fetch(url):
    fetch_calls.append(url)
    if url.endswith('/package/libopenssl/libopenssl.mk'):
        assert f'/{sha}/' in url
        return 'LIBOPENSSL_VERSION = 3.6.5\n'
    if url == 'https://openssl-library.org/source/':
        return openssl_table([('3.6', 'openssl-3.6.5.tar.gz', '01 Nov 2026')])
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
        return '[{"tag_name":"1.7.12"}]'
    if "koalaman/shellcheck" in url:
        return '[{"tag_name":"0.11.0"}]'
    if "hadolint/hadolint" in url:
        return '[{"tag_name":"v2.15.1"}]'
    if "kernel-hardening-checker" in url:
        assert "/tags?" in url
        return '[{"name":"v0.6.17.1"}]'
    if "aquasecurity/trivy" in url:
        return '[{"tag_name":"v0.76.0"}]'
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
    assert '| OpenSSL (Buildroot target/host) | `3.6.5` | `3.6.5` | 最新 |' in report
    assert '| OpenSSL upstream support | `3.6.5` | `2026-11-01` | 参考 |' in report
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
    assert "| Debian snapshot date | `20261103T023120Z` | `-` | 最新 |" in report
    assert "| Buildroot LTS | `2026.08.x` | `2025.02.x` | 参考 |" in report
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

openssl_downloads = openssl_table([
    ('3.5 [LTS]', 'openssl-3.5.9.tar.gz', '08 Apr 2030'),
    ('4.0', 'openssl-4.0.3.tar.gz', '14 May 2027'),
    ('4.1', 'openssl-4.1.0.tar.gz', '23 Nov 2027'),
])


def openssl_fetch(url):
    if url == 'https://openssl-library.org/source/':
        return openssl_downloads
    if url == 'https://openssl-library.org/policies/releasestrat/':
        return '<li>Version <b>3.6</b> will be supported until 2026-11-01</li>'
    return fake_fetch(url)


with patch.object(module, 'fetch', openssl_fetch):
    rows = module.openssl_rows(passed, date(2026, 11, 2))
    assert rows[0][1:4] == ('3.6.5', '4.1.0', '更新あり')
    assert rows[1][1:4] == ('3.6.5', '2026-11-01', '保守期限超過')
    assert module.upstream_summary([rows[1]]) == '更新あり'
with patch.object(module, 'fetch', fake_fetch):
    for day, expected in [(date(2026, 11, 1), '参考'), (date(2026, 11, 2), '保守期限超過')]:
        assert module.openssl_rows(passed, day)[1][1:4] == ('3.6.5', '2026-11-01', expected)
print('ok - compares all OpenSSL stable series and checks the exact expiry boundary')

override_file = passed / 'board/cardputerzero/package-overrides.mk'
override_file.write_text('override LIBOPENSSL_VERSION = 3.5.9\n')
for recipe, expected in [('3.5.8', '参考'), ('3.5.9', '廃止検討'),
                         ('3.5.10', '廃止検討'), ('4.0.3', '廃止検討'),
                         ('3.6.5', '参考')]:
    def override_fetch(url):
        if url.endswith('/2026.08.x/package/libopenssl/libopenssl.mk'):
            return f'LIBOPENSSL_VERSION = {recipe}\n'
        return openssl_fetch(url)
    with patch.object(module, 'fetch', override_fetch):
        rows = module.openssl_rows(passed, date(2026, 11, 12))
    assert rows[0][1:4] == ('3.5.9', '3.5.9', '最新')
    assert rows[1][1:4] == ('3.5.9', '2030-04-08', '参考')
    assert rows[2][3] == '参考'  # The pinned 3.6 recipe is unsupported.
    assert rows[3][2:4] == (recipe, expected)
    assert module.upstream_summary([rows[3]]) == ('更新あり' if expected == '廃止検討' else '全て最新')
with patch.object(module, 'fetch', lambda url: override_fetch(url).replace(
        'openssl-3.5.9.tar.gz', 'openssl-3.5.10.tar.gz')):
    assert module.openssl_rows(passed, date(2026, 11, 12))[0][1:4] == ('3.5.9', '3.5.10', '更新あり')
for today, expected in [(date(2027, 5, 14), '廃止検討'), (date(2027, 5, 15), '参考')]:
    with patch.object(module, 'fetch', lambda url: (
            'LIBOPENSSL_VERSION = 4.0.3\n' if '/2026.08.x/' in url else openssl_fetch(url))):
        assert module.openssl_rows(passed, today)[3][3] == expected
for contents in ('', 'override LIBOPENSSL_VERSION = invalid\n',
                 'override LIBOPENSSL_VERSION = 3.5.9\n' * 2):
    override_file.write_text(contents)
    assert module.openssl_rows(passed, date(2026, 11, 12))[0][3] == '確認できず'
override_file.write_text('override LIBOPENSSL_VERSION = 3.5.9\n')
with patch.object(module, 'fetch', side_effect=OSError('offline')), contextlib.redirect_stderr(io.StringIO()):
    assert module.upstream_summary(module.openssl_rows(passed, date(2026, 11, 12))) == '更新あり'
override_file.unlink()
print('ok - monitors the override series, supported retirement candidates and invalid/offline inputs')

for bad in (
    '', openssl_downloads.replace('End-of-Life', 'Unknown'),
    openssl_downloads.replace('openssl-4.1.0', 'openssl-4.1.0-rc1'),
    openssl_downloads.replace('23 Nov 2027', '31 Nov 2027'),
    openssl_downloads.replace('23 Nov 2027', '01 Sep 2026'),
    openssl_downloads.replace('<td>4.1</td>', '<td>4.0</td>'),
    openssl_downloads + openssl_downloads,
):
    try:
        module.parse_openssl_downloads(bad)
    except ValueError:
        pass
    else:
        raise AssertionError('Accepted malformed OpenSSL release data')
print('ok - rejects missing, malformed, prerelease, duplicate and conflicting OpenSSL rows')

for failed_url in (
    'https://openssl-library.org/source/',
    'https://openssl-library.org/policies/releasestrat/',
    f'https://raw.githubusercontent.com/buildroot/buildroot/{sha}/package/libopenssl/libopenssl.mk',
):
    def unavailable(url):
        if url == failed_url:
            raise OSError('fixture unavailable')
        return openssl_fetch(url)
    with patch.object(module, 'fetch', unavailable), contextlib.redirect_stderr(io.StringIO()):
        rows = module.openssl_rows(passed, date(2026, 11, 2))
    assert any(row[3] == '確認できず' for row in rows)
    assert module.upstream_summary(rows) == '更新あり'
print('ok - OpenSSL recipe, release or policy failure never reports all current')

for policy in ('', 'Version 3.6 will be supported until 2026-02-30',
               'Version 3.6 will be supported until 2030-11-01',
               'Version 3.6 will be supported until 2026-11-01 ' * 2):
    def invalid_policy(url):
        if url.endswith('/policies/releasestrat/'):
            return policy
        return openssl_fetch(url)
    with patch.object(module, 'fetch', invalid_policy), contextlib.redirect_stderr(io.StringIO()):
        assert module.openssl_rows(passed, date(2026, 11, 2))[1][3] == '確認できず'
print('ok - missing, invalid or ambiguous lifecycle deadlines stay unknown')

workflow = (root / '.github/workflows/pins-check.yml').read_text()
import re
import subprocess
issue_filter = re.search(r"if grep -qvE '([^']+)'", workflow)[1]
for state, actionable in [('参考', False), ('保守期限超過', True), ('確認できず', True)]:
    report = '| 依存 | 固定値 | 最新 | 状態 | 参照URL |\n|---|---|---|---|---|\n'
    report += f'| OpenSSL upstream support | `3.6.5` | `2026-11-01` | {state} | https://example.com |\n'
    result = subprocess.run(['grep', '-qvE', issue_filter], input=report, text=True)
    assert result.returncode == (0 if actionable else 1)
print('ok - weekly Issue filter keeps expired and unknown support findings open')

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
        assert module.upstream(report_path, passed, today=date(2026, 12, 4)) == 0
    report = report_path.read_text()
    assert "| Debian snapshot date | `20261103T023120Z` | `-` | 更新あり |" in report
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
