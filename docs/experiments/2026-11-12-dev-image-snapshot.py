#!/usr/bin/env python3
"""Collect signed snapshot metadata for this maintenance experiment."""

import argparse
import concurrent.futures
import csv
import hashlib
import json
import lzma
from pathlib import Path
import re
import subprocess
from urllib.parse import quote
from urllib.request import urlopen


OLD = "20261103T023120Z"
PREVIOUS = "20261106T203307Z"
NEW = "20261107T075304Z"
FIXES = {
    "apt": "3.0.4",
    "libapt-pkg7.0": "3.0.4",
    "zlib1g": "1:1.3.dfsg+really1.3.1-1+deb13u1",
    "zlib1g-dev": "1:1.3.dfsg+really1.3.1-1+deb13u1",
}
ARCHES = ("amd64", "arm64")


def fetch(url, path):
    with urlopen(url, timeout=120) as response:
        data = response.read()
    with path.open("xb") as stream:
        stream.write(data)
    return data


def metadata(output, keyring_image):
    output.mkdir()
    keyring = output / "debian-archive-keyring.gpg"
    keyring.write_bytes(subprocess.check_output([
        "docker", "run", "--rm", "--entrypoint", "cat", keyring_image,
        "/usr/share/keyrings/debian-archive-keyring.gpg",
    ]))
    first_seen = []
    for package, version in FIXES.items():
        url = f"https://snapshot.debian.org/mr/binary/{package}/{quote(version, safe='')}/binfiles"
        binaries = json.loads(fetch(url, output / f"{package}-binfiles.json"))
        for row in binaries["result"]:
            if row["architecture"] not in ARCHES:
                continue
            info_url = f"https://snapshot.debian.org/mr/file/{row['hash']}/info"
            info = json.loads(fetch(info_url, output / f"{package}-{row['architecture']}.json"))
            first_seen.append(min(r["first_seen"] for r in info["result"]))
    assert max(first_seen) == NEW
    calendar_url = "https://snapshot.debian.org/archive/debian-security/?year=2026&month=11"
    calendar = fetch(calendar_url, output / "calendar.html").decode()
    timestamps = sorted(set(re.findall(r"202611[0-9]{2}T[0-9]{6}Z", calendar)))
    assert timestamps[timestamps.index(NEW) - 1] == PREVIOUS

    def release(job):
        snapshot, archive, suite = job
        stem = f"{snapshot}-{archive}-{suite}"
        url = f"https://snapshot.debian.org/archive/{archive}/{snapshot}/dists/{suite}"
        signed = output / f"{stem}-InRelease"
        fetch(f"{url}/InRelease", signed)
        decoded = subprocess.run([
            "gpgv", "--keyring", str(keyring.resolve()), "--output", "-", str(signed),
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
        (output / f"{stem}-Release").write_bytes(decoded)
        sha_lines = decoded.decode().split("\nSHA256:\n", 1)[1].split("\n\n", 1)[0]
        files = {}
        for line in sha_lines.splitlines():
            fields = line.split()
            if len(fields) == 3 and re.fullmatch("[0-9a-f]{64}", fields[0]):
                files[fields[2]] = fields[:2]
        rows = []
        for arch in ARCHES:
            relative = f"main/binary-{arch}/Packages.xz"
            digest, size = files[relative]
            packed = fetch(f"{url}/{relative}", output / f"{stem}-{arch}-Packages.xz")
            assert len(packed) == int(size) and hashlib.sha256(packed).hexdigest() == digest
            for paragraph in lzma.decompress(packed).decode().split("\n\n"):
                fields = dict(line.split(": ", 1) for line in paragraph.splitlines()
                              if line and not line[0].isspace() and ": " in line)
                if fields.get("Package") in FIXES:
                    rows.append((snapshot, archive, suite, arch, fields["Package"],
                                 fields["Version"], fields.get("SHA256", "")))
        return rows

    jobs = [(s, a, suite) for s in (OLD, PREVIOUS, NEW)
            for a, suite in (("debian", "trixie"), ("debian", "trixie-updates"),
                             ("debian-security", "trixie-security"))]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = [row for group in pool.map(release, jobs) for row in group]
    for snapshot in (PREVIOUS, NEW):
        satisfied = all(any(r[0] == snapshot and r[3] == arch and r[4] == name
                            and subprocess.run(["dpkg", "--compare-versions", r[5], "ge", version],
                                               check=False).returncode == 0 for r in rows)
                        for name, version in FIXES.items() for arch in ARCHES)
        assert satisfied == (snapshot == NEW)
    with (output / "candidates.csv").open("x") as stream:
        writer = csv.writer(stream)
        writer.writerow(("snapshot", "archive", "suite", "arch", "package", "version", "sha256"))
        writer.writerows(sorted(rows))
    with (output / "sources.csv").open("x") as stream:
        writer = csv.writer(stream)
        writer.writerow(("file", "bytes", "sha256"))
        for path in sorted(output.iterdir()):
            if path.is_file() and path.name != "sources.csv":
                data = path.read_bytes()
                writer.writerow((path.name, len(data), hashlib.sha256(data).hexdigest()))
    print(f"ok - signed indexes and first_seen: earliest={NEW}; previous={PREVIOUS} rejected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--keyring-image", default="msd-dev-snapshot:old")
    args = parser.parse_args()
    metadata(args.output, args.keyring_image)
