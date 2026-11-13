#!/usr/bin/env python3
"""Add verified supplementary material without changing Buildroot legal-info."""

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / "board/cardputerzero/legal-info"
BOOTLIN_HASH = "toolchain/toolchain-external/toolchain-external-bootlin/toolchain-external-bootlin.hash"


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked(data, expected, name):
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError(f"invalid pinned SHA-256: {name}")
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"SHA-256 mismatch: {name}")
    return data


def relative(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError(f"unsafe license path: {value}")
    return path


def download(url):
    if not url.startswith("https://toolchains.bootlin.com/downloads/releases/licenses/"):
        raise ValueError(f"unsupported license URL: {url}")
    with urlopen(url, timeout=60) as response:
        if not response.geturl().startswith("https://"):
            raise ValueError("license download redirected outside HTTPS")
        data = response.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise ValueError("license text exceeds 2 MiB")
    return data


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE).decode().strip()


def inventory(directory):
    return {str(p.relative_to(directory)): sha256(p)
            for p in sorted(directory.rglob("*")) if p.is_file()}


def collect(repo, legal, sdk, pins_path, readme_path, license_dir=None):
    repo, legal, sdk = repo.resolve(), legal.resolve(), sdk.resolve()
    if license_dir is not None:
        license_dir = license_dir.resolve()
    for path in [legal / name for name in ["README", "manifest.csv", "host-manifest.csv", "buildroot.config"]]:
        if not path.is_file():
            raise ValueError(f"missing legal-info input: {path.name}")
    if (legal / "supplement").exists():
        raise FileExistsError("supplement already exists; use a fresh legal-info output")
    pins = json.loads(pins_path.read_text())
    if pins["schema"] != 1 or not pins["components"]:
        raise ValueError("empty or unsupported Bootlin metadata")
    for name, digest in pins["metadata_sha256"].items():
        path = sdk / relative(name)
        checked(path.read_bytes(), digest, name)
    if (sdk / "README.txt").read_text().splitlines()[0] != pins["toolchain"]:
        raise ValueError("Bootlin toolchain identity mismatch")
    with (sdk / "summary.csv").open() as stream:
        summary = list(csv.DictReader(stream))
    actual = {(r["PACKAGE"], r["VERSION"]) for r in summary}
    expected = {(c["component"], c["version"]) for c in pins["components"]}
    if actual != expected or len(expected) != len(pins["components"]):
        raise ValueError("component/version inventory differs from Bootlin summary")
    if "BR2_TOOLCHAIN_EXTERNAL_BOOTLIN_AARCH64_GLIBC_STABLE=y" not in (
            legal / "buildroot.config").read_text().splitlines():
        raise ValueError("legal-info configuration does not select the pinned Bootlin toolchain")
    line = git(repo, "ls-tree", "HEAD", "vendor/buildroot")
    match = re.fullmatch(r"160000 commit ([0-9a-f]{40})\tvendor/buildroot", line)
    if not match:
        raise ValueError("missing Buildroot gitlink in HEAD")
    commit = match[1]
    source = repo / "vendor/buildroot"
    git(source, "cat-file", "-e", commit + "^{commit}")
    hashes = git(source, "show", f"{commit}:{BOOTLIN_HASH}")
    archive_name = pins["toolchain"] + ".tar.xz"
    if not re.search(r"^sha256\s+" + pins["toolchain_archive_sha256"] + r"\s+" +
                     re.escape(archive_name) + r"$", hashes, re.M):
        raise ValueError("Bootlin archive pin differs from the Buildroot gitlink")
    original = inventory(legal)
    with tempfile.TemporaryDirectory(prefix=".legal-supplement-", dir=legal.parent) as temporary:
        stage = Path(temporary) / "supplement"
        stage.mkdir()
        archive = f"buildroot-{commit}.tar.gz"
        tar = Path(temporary) / "buildroot.tar"
        subprocess.run(["git", "-C", str(source), "archive", "--format=tar",
                        f"--prefix=buildroot-{commit}/", "--output=" + str(tar), commit], check=True)
        with tar.open("rb") as inp, (stage / archive).open("wb") as out:
            with gzip.GzipFile(filename="", fileobj=out, mode="wb", mtime=0) as compressed:
                shutil.copyfileobj(inp, compressed)
        metadata = stage / "metadata"
        metadata.mkdir()
        shutil.copyfile(pins_path, metadata / "bootlin-pins.json")
        for name in pins["metadata_sha256"]:
            target = metadata / relative(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(sdk / name, target)
        components = []
        archives = {}
        for component in pins["components"]:
            record = dict(component, source_status="uncollected", patch_status="uncollected")
            licenses = []
            for license in component["licenses"]:
                path = relative(license["path"])
                data = ((license_dir / path).read_bytes() if license_dir is not None
                        else download(license["url"]))
                checked(data, license["sha256"], str(path))
                target = stage / "licenses" / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                licenses.append(dict(license, status="collected/hash-verified",
                                     collected_path=str(target.relative_to(stage))))
            record["licenses"] = licenses
            record["license_status"] = "collected/hash-verified" if licenses else "uncollected"
            components.append(record)
            if component["source_archive"] != "not saved":
                archives[component["source_url"]] = {
                    "url": component["source_url"], "bytes": component["source_bytes"],
                    "hashes": component["source_hashes"], "status": "uncollected/reference-hash-only"}
        manifest = {
            "schema": 1,
            "project_commit": git(repo, "rev-parse", "HEAD"),
            "collector_sha256": sha256(Path(__file__)),
            "buildroot": {"gitlink_commit": commit, "archive": archive,
                          "sha256": sha256(stage / archive), "status": "collected/git-archive"},
            "bootlin": {k: pins[k] for k in ["toolchain", "toolchain_archive_sha256", "builder_commit"]},
            "components": components,
            "original_files_sha256": original,
            "uncollected": {
                "source_archives": list(archives.values()),
                "source_archive_bytes": sum(a["bytes"] for a in archives.values()),
                "patches": [c["patch_location"] for c in components],
                "bootlin_builder_tree": pins["builder_commit"],
                "linux_headers_license": "5.4.296; no license file declared in SDK summary",
                "external_tree_archive": "not collected; project commit and collector hash recorded",
            },
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        fields = ["component", "version", "source_url", "source_sha256", "source_sha512",
                  "source_status", "patch_location", "patch_status", "license_file",
                  "license_status", "license_sha256"]
        with (stage / "manifest.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for component in components:
                for license in component["licenses"] or [{}]:
                    writer.writerow({
                        "component": component["component"], "version": component["version"],
                        "source_url": component["source_url"],
                        "source_sha256": component["source_hashes"].get("sha256", ""),
                        "source_sha512": component["source_hashes"].get("sha512", ""),
                        "source_status": component["source_status"],
                        "patch_location": component["patch_location"], "patch_status": "uncollected",
                        "license_file": license.get("collected_path", ""),
                        "license_status": component["license_status"],
                        "license_sha256": license.get("sha256", ""),
                    })
        (stage / "README.md").write_bytes(readme_path.read_bytes())
        (stage / "SHA256SUMS").write_text("".join(
            f"{digest}  {path}\n" for path, digest in inventory(stage).items()))
        if inventory(legal) != original:
            raise ValueError("original legal-info changed during collection")
        stage.rename(legal / "supplement")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Buildroot O= directory")
    parser.add_argument("--license-dir", type=Path, help="offline license tree; no downloads")
    args = parser.parse_args()
    try:
        result = collect(ROOT, args.output / "legal-info", args.output / "host/opt/ext-toolchain",
                         INPUTS / "bootlin-2025.08-1.json", INPUTS / "README.md", args.license_dir)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"error: legal-info supplement: {error}", file=sys.stderr)
        return 1
    count = sum(len(c["licenses"]) for c in result["components"])
    print(f"ok - supplement: Buildroot {result['buildroot']['gitlink_commit']}, "
          f"{len(result['components'])} components, {count} verified license files")
    print(f"uncollected - {len(result['uncollected']['source_archives'])} source archives; "
          "patches; Bootlin builder tree; Linux headers 5.4.296 license")
    return 0


if __name__ == "__main__":
    sys.exit(main())
