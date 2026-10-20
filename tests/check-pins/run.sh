#!/bin/sh
set -eu

repo_root="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"

python3 - "$repo_root" <<'PY'
import contextlib
import importlib.util
import io
import lzma
import pathlib
import shutil
import sys
import tempfile

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
    (path / "docker").mkdir()
    (path / "configs/msd_cardputerzero_defconfig").write_text(
        f'BR2_LINUX_KERNEL_CUSTOM_TARBALL_LOCATION="linux-{sha}.tar.gz"\n'
        f'BR2_LINUX_KERNEL_CUSTOM_TARBALL_LOCATION="linux-{sha}.tar.gz"\n'
    )
    (path / "board/cardputerzero/patches/linux/linux.hash").write_text(
        f"sha256 deadbeef linux-{sha}.tar.gz\n"
    )
    (path / "package/m5stack-cardputerzero/m5stack-cardputerzero.mk").write_text(
        "M5STACK_CARDPUTERZERO_VERSION := $(shell git -C $(M5STACK_CARDPUTERZERO_SITE) rev-parse HEAD)\n"
    )
    (path / ".github/workflows/lint.yml").write_text(
        "env:\n"
        "  ACTIONLINT_VERSION: 1.7.12\n"
        "  SHELLCHECK_VERSION: 0.11.0\n"
        "  HADOLINT_VERSION: 2.15.1\n"
        "          printf '%s  %s\\n' \\\\\n"
        "            8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8 \\\\\n"
        "            \"$actionlint_archive\" | sha256sum -c -\n"
        "          printf '%s  %s\\n' \\\\\n"
        "            8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198 \\\\\n"
        "            \"$shellcheck_archive\" | sha256sum -c -\n"
        "jobs:\n  lint:\n    runs-on: ubuntu-26.04\n"
    )
    (path / "docker/msd-dev.Dockerfile").write_text(
        "ARG DEBIAN_SNAPSHOT=20261019T190000Z\n"
        "ARG QEMU_DEB_VERSION=1:11.0.2+ds-2~bpo13+1\n"
        "ARG ACTIONLINT_VERSION=1.7.12\n"
        "ARG ACTIONLINT_SHA256=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8\n"
        "ARG SHELLCHECK_VERSION=0.11.0\n"
        "ARG SHELLCHECK_SHA256=8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198\n"
    )
    (path / ".github/workflows/build.yml").write_text(
        "env:\n"
        "  KHC_TAG: v0.6.17.1\n"
        "  KHC_COMMIT: afc376f2a935994793343cfeb05953583cc30191\n"
        "jobs:\n  build:\n    runs-on: ubuntu-26.04\n"
    )
    (path / ".github/actionlint.yaml").write_text(
        'paths:\n  .github/workflows/*.yml:\n    ignore:\n      - \'label "ubuntu-26.04" is unknown\'\n'
    )
    (path / ".gitmodules").write_text(
        '[submodule "vendor/buildroot"]\n\tpath = vendor/buildroot\n\turl = https://example.test/buildroot\n\tbranch = 2026.08.x\n'
    )
    (path / "README.md").write_text("| ビルド | Buildroot 2026.08 |\n")
    return path


passed = fixture()
assert module.consistency(passed) == []
print("ok - consistency accepts a matching fixture")

bad_docker_tool_pin = fixture()
dockerfile = bad_docker_tool_pin / "docker/msd-dev.Dockerfile"
dockerfile.write_text(dockerfile.read_text().replace(
    "ARG ACTIONLINT_VERSION=1.7.12",
    "ARG ACTIONLINT_VERSION=1.7.11",
))
assert any("ACTIONLINT_VERSION" in error for error in module.consistency(bad_docker_tool_pin))
print("ok - detects Dockerfile tool version drift")

bad_docker_hash = fixture()
dockerfile = bad_docker_hash / "docker/msd-dev.Dockerfile"
dockerfile.write_text(dockerfile.read_text().replace(
    "ARG SHELLCHECK_SHA256=8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198",
    "ARG SHELLCHECK_SHA256=" + "0" * 64,
))
assert any("SHELLCHECK_SHA256" in error for error in module.consistency(bad_docker_hash))
print("ok - detects Dockerfile checksum drift")

bad_hash = fixture()
(bad_hash / "board/cardputerzero/patches/linux/linux.hash").write_text(
    "sha256 deadbeef linux-" + "0" * 40 + ".tar.gz\n"
)
assert any("linux.hash" in error for error in module.consistency(bad_hash))
print("ok - detects a mismatched linux.hash")

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
assert module.parse_runner_labels("| `ubuntu-24.04` | beta image |\n") == [
    ("ubuntu-24.04", "beta")
]
print("ok - parses ls-remote, .gitmodules, releases, and runner README data")

def fake_run(*args, cwd=None):
    if any("raspberrypi/linux.git" in arg for arg in args):
        return (
            f"{sha}\trefs/heads/rpi-6.18.y\n"
            f"{'a' * 40}\trefs/heads/rpi-7.3.y\n"
        )
    return (
        f"{'b' * 40}\trefs/heads/2026.08.x\n"
        f"{'c' * 40}\trefs/heads/2026.02.x\n"
    )


def fake_fetch(url):
    if "rhysd/actionlint" in url:
        return '{"tag_name":"1.7.12"}'
    if "koalaman/shellcheck" in url:
        return '{"tag_name":"0.11.0"}'
    if "hadolint/hadolint" in url:
        return '{"tag_name":"v2.15.1"}'
    if "kernel-hardening-checker" in url:
        return '{"tag_name":"v0.6.17.1"}'
    return "| `ubuntu-26.04` | current image |\n"


def fake_fetch_bytes(url):
    packages = (
        "Package: qemu-system-arm\nVersion: 1:11.0.2+ds-2~bpo13+1\n\n"
        "Package: qemu-utils\nVersion: 1:11.0.2+ds-2~bpo13+1\n\n"
    ).encode()
    return lzma.compress(packages)


module.run = fake_run
module.fetch = fake_fetch
module.fetch_bytes = lambda url: lzma.compress(
    b"Package: qemu-system-arm\nVersion: 1:11.0.2+ds-2~bpo13+1\n\n"
)
with tempfile.TemporaryDirectory() as directory:
    report_path = pathlib.Path(directory) / "pins.md"
    with contextlib.redirect_stdout(io.StringIO()):
        assert module.upstream(report_path, passed) == 0
    report = report_path.read_text()
    assert (
        "| QEMU (Debian trixie-backports) | `1:11.0.2+ds-2~bpo13+1` | "
        "`確認できず` | 確認できず |"
        in report
    )
print("ok - reports an incomplete Debian QEMU index as unknown")

module.fetch_bytes = fake_fetch_bytes
with tempfile.TemporaryDirectory() as directory:
    report_path = pathlib.Path(directory) / "pins.md"
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert module.upstream(report_path, passed) == 0
    report = report_path.read_text()
    assert (
        "| Raspberry Pi Linux series | `rpi-6.18.y` | `rpi-7.3.y` | 参考 |"
        in report
    )
    assert (
        "| QEMU (Debian trixie-backports) | `1:11.0.2+ds-2~bpo13+1` | "
        "`1:11.0.2+ds-2~bpo13+1` | 最新 |"
        in report
    )
    assert "| Debian snapshot date | `20261019T190000Z` | `-` | 参考 |" in report
    assert "| Buildroot LTS | `2026.08.x` | `2026.02.x` | 参考 |" in report
    assert output.getvalue().strip() == "全て最新"
print("ok - marks informational upstream rows as 参考 and excludes them from status")

for path in fixtures:
    shutil.rmtree(path)
PY

issue_pattern='^([|]---.*|[|] 依存 [|].*|[|].*[|] (最新|参考) [|].*[|])$'
reference_report='| 依存 | 固定値 | 最新 | 状態 | 参照URL |
|---|---|---|---|---|
| Raspberry Pi Linux series | rpi-6.18.y | rpi-7.3.y | 参考 | https://example.test |
| Buildroot LTS | 2026.08.x | 2026.02.x | 参考 | https://example.test |'
if printf '%s\n' "$reference_report" | grep -qvE "$issue_pattern"; then
    echo "fail - informational rows must not trigger an issue" >&2
    exit 1
fi
echo "ok - ignores 参考 rows when deciding whether to open or update the issue"

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
