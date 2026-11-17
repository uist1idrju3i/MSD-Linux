#!/usr/bin/env python3
"""Verify official NVD JSON 2.0 feeds and atomically publish a local snapshot."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import urllib.request
import zlib


BASE_URL = "https://nvd.nist.gov/feeds/json/cve/2.0/"
SAFE_WINDOW = 7 * 86400
MAX_AGE = 86400
MAX_COMPRESSED = 256 * 1024 * 1024
MAX_JSON = 1024 * 1024 * 1024
CVE_ID = re.compile(r"CVE-([0-9]{4})-([0-9]{4,})")


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return int(result.timestamp())


def check_freshness(synced_at, modified_at, now):
    for value in (synced_at, modified_at):
        if type(value) is not int or value > now + 300 or now - value > MAX_AGE:
            raise ValueError("監視不能: NVD verified sync or modified meta is older than 24 hours / invalid")


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "MSD-Linux-NVD/1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        if not response.url.startswith(BASE_URL):
            raise ValueError("unexpected NVD redirect")
        data = response.read(MAX_COMPRESSED + 1)
    if len(data) > MAX_COMPRESSED:
        raise ValueError("NVD response is too large")
    return data


def read_feed(name, now, retrieve=download):
    url = BASE_URL + f"nvdcve-2.0-{name}"
    raw_meta = retrieve(url + ".meta").decode("utf-8")
    meta = dict(line.split(":", 1) for line in raw_meta.splitlines() if line)
    size, gz_size = int(meta["size"]), int(meta["gzSize"])
    modified = timestamp(meta["lastModifiedDate"])
    if not 0 < size <= MAX_JSON or not 0 < gz_size <= MAX_COMPRESSED:
        raise ValueError("invalid NVD meta size")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", meta["sha256"]):
        raise ValueError("invalid NVD meta SHA-256")
    if name == "modified":
        check_freshness(now, modified, now)
    compressed = retrieve(url + ".json.gz")
    if len(compressed) != gz_size:
        raise ValueError("NVD gzip size mismatch")
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        data = stream.read(size + 1)
    if len(data) != size or hashlib.sha256(data).hexdigest() != meta["sha256"].lower():
        raise ValueError("NVD JSON size or SHA-256 mismatch")
    payload = json.loads(data)
    entries = payload.get("vulnerabilities") if isinstance(payload, dict) else None
    if (not isinstance(payload, dict) or payload.get("format") != "NVD_CVE" or payload.get("version") != "2.0"
            or not isinstance(entries, list) or payload.get("totalResults") != len(entries)):
        raise ValueError("invalid NVD feed envelope")
    seen = set()
    for entry in entries:
        cve = entry.get("cve") if isinstance(entry, dict) else None
        if not isinstance(cve, dict) or not CVE_ID.fullmatch(cve.get("id", "")):
            raise ValueError("invalid NVD CVE object")
        if cve["id"] in seen:
            raise ValueError("duplicate CVE ID within feed")
        seen.add(cve["id"])
    return [entry["cve"] for entry in entries], {
        "url": url + ".json.gz", "meta": meta, "meta_text": raw_meta,
        "retrieved_at": now, "count": len(entries),
    }


def entry_path(root, cve_id):
    match = CVE_ID.fullmatch(cve_id)
    if match is None:
        raise ValueError("invalid CVE ID")
    year, number = match.groups()
    return root / "git" / f"CVE-{year}" / f"CVE-{year}-{number[:-2]}xx" / f"{cve_id}.json"


def content_identity(root):
    digest = hashlib.sha256()
    paths = sorted((root / "git").glob("CVE-*/CVE-*/*.json"))
    for path in paths:
        data = path.read_bytes()
        cve = json.loads(data)
        if path != entry_path(root, cve["id"]):
            raise ValueError("cached CVE path does not match ID")
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest(), len(paths)


def refresh(output, now=None, retrieve=download):
    realtime = now is None
    now = int(time.time()) if now is None else now
    output = Path(output).absolute()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not output.is_symlink():
        raise ValueError("--nvd-path must be a snapshot symlink, not an existing directory")
    previous = output.resolve() if output.exists() else None
    cached = None
    if previous is not None:
        cached = json.loads((previous / "manifest.json").read_text())
        if cached.get("schema") != 1 or cached.get("source") != BASE_URL:
            raise ValueError("invalid cached NVD manifest")
        synced = cached.get("synced_at")
        if type(synced) is not int or synced > now + 300:
            raise ValueError("invalid cached sync time")
        if now - synced >= SAFE_WINDOW:
            cached = None
        elif content_identity(previous) != (cached["snapshot_id"], cached["count"]):
            raise ValueError("cached NVD snapshot content mismatch")
    stage = Path(tempfile.mkdtemp(prefix="snapshot-", dir=output.parent))
    link = output.parent / (stage.name + ".link")
    promoted = False
    started = time.monotonic()
    try:
        sources = []
        if cached is not None:
            shutil.copytree(previous / "git", stage / "git")
            sources = cached["sources"].copy()
        else:
            for year in range(2002, datetime.fromtimestamp(now, timezone.utc).year + 1):
                entries, source = read_feed(str(year), now, retrieve)
                sources.append(source)
                write_entries(stage, entries)
                print(f"verified year={year} count={len(entries)}", flush=True)
        entries, source = read_feed("modified", now, retrieve)
        sources.append(source)
        write_entries(stage, entries)
        snapshot_id, count = content_identity(stage)
        if count == 0:
            raise ValueError("NVD snapshot has zero CVEs")
        finished = int(time.time()) if realtime else now
        coverage_start = cached["synced_at"] if cached is not None else now
        if finished - coverage_start >= SAFE_WINDOW:
            raise ValueError("NVD refresh exceeded the safe coverage window")
        modified_at = timestamp(source["meta"]["lastModifiedDate"])
        check_freshness(finished, modified_at, finished)
        manifest = {
            "schema": 1, "source": BASE_URL, "snapshot_id": snapshot_id,
            "synced_at": finished, "modified_at": modified_at,
            "retrieved_at": now,
            "count": count, "sources": sources,
            "mode": "incremental" if cached is not None else "bootstrap",
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        link.symlink_to(stage.name, target_is_directory=True)
        os.replace(link, output)
        promoted = True
        if (previous is not None and previous.parent == output.parent
                and previous.name.startswith("snapshot-")):
            shutil.rmtree(previous)
        print(f"snapshot={snapshot_id} count={count} mode={manifest['mode']} "
              f"seconds={time.monotonic() - started:.3f}", flush=True)
        return manifest
    finally:
        link.unlink(missing_ok=True)
        if not promoted:
            shutil.rmtree(stage)


def write_entries(root, entries):
    for cve in entries:
        path = entry_path(root, cve["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cve, sort_keys=True, ensure_ascii=False,
                                   separators=(",", ":")) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nvd-path", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    try:
        manifest = refresh(args.nvd_path)
        if args.github_output:
            with args.github_output.open("a") as stream:
                stream.write(f"snapshot={manifest['snapshot_id']}\n")
                stream.write(f"synced-at={manifest['synced_at']}\n")
        return 0
    except (OSError, ValueError, KeyError, TypeError, EOFError, zlib.error) as error:
        print(f"fetch-nvd: 監視不能: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
