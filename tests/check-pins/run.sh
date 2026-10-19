#!/bin/sh
set -eu

repo_root="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"

python3 - "$repo_root" <<'PY'
import importlib.util
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
    (path / ".github/workflows/lint.yml").write_text("jobs:\n  lint:\n    runs-on: ubuntu-26.04\n")
    (path / ".github/workflows/build.yml").write_text("jobs:\n  build:\n    runs-on: ubuntu-26.04\n")
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
for path in fixtures:
    shutil.rmtree(path)
PY
