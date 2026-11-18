#!/usr/bin/env python3
"""Hash-only smoke images and content-addressed, verified non-image evidence."""

import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import tarfile
import uuid

import smoke_profile
from supervisor import load_json, write_json

MODE = "shared-nonimage-sha256/1"
IMAGES = {"sdcard.img", "build/rootfs-fs-compare.squashfs"}


def verify_object(root, row):
    import storage
    path = root / row["sha256"]
    if path.is_symlink() or not path.is_file() or path.stat().st_size != row["size"]:
        raise ValueError("missing or invalid shared evidence object")
    with path.open("rb") as stream:
        if storage.digest(stream) != row["sha256"]:
            raise ValueError("shared evidence object hash mismatch")


def verify(path, archive, manifest):
    import storage
    if (manifest.get("schema") != storage.SCHEMA or manifest.get("mode") != MODE
            or not re.fullmatch(r"[0-9a-f]{64}", manifest.get("profile", ""))
            or archive.getnames() != [storage.MANIFEST]
            or set(manifest.get("omitted_images", [])) != IMAGES):
        raise ValueError("invalid shared smoke archive")
    entries = {row["path"]: row for row in manifest["entries"]}
    if len(entries) != len(manifest["entries"]):
        raise ValueError("duplicate shared evidence entry")
    root = Path(path).parent / "objects"
    for name, row in entries.items():
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise ValueError("invalid object digest")
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("unsafe evidence path")
        if name in IMAGES:
            if row["type"] != "file":
                raise ValueError("omitted image must be a regular file")
            continue
        if row["type"] in ("file", "hardlink"):
            if row["type"] == "hardlink":
                target = entries.get(row["link"], {})
                if (target.get("type") != "file" or target["path"] in IMAGES
                        or any(target[key] != row[key] for key in ("sha256", "size", "mode", "mtime_ns"))):
                    raise ValueError("invalid shared evidence hardlink")
            verify_object(root, row)
        elif row["type"] not in ("directory", "symlink", "character", "block", "fifo"):
            raise ValueError("unknown shared evidence type")
        elif row["sha256"] != hashlib.sha256(os.fsencode(row["link"])).hexdigest():
            raise ValueError("invalid evidence metadata digest")
    return manifest


def store(source, row, root):
    import storage
    target = root / row["sha256"]
    if not target.exists():
        temporary = root / f".{uuid.uuid4().hex}.partial"
        with (source / row["path"]).open("rb") as src, temporary.open("xb") as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        with temporary.open("rb") as stream:
            if temporary.stat().st_size != row["size"] or storage.digest(stream) != row["sha256"]:
                raise ValueError("source changed while storing shared evidence")
        try:
            os.link(temporary, target)
        except FileExistsError:
            pass
        storage.sync_directory(root)
        temporary.unlink()
    verify_object(root, row)


def archive_attempt(source, destination):
    import fcntl
    import storage
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or source in destination.parents:
        raise ValueError("archive destination must be outside the source")
    destination.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(os.fsencode(source)).hexdigest()
    with (destination / f".{key}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state_path = source / storage.STATE
        state = load_json(state_path) if state_path.exists() else None
        if state and state.get("complete"):
            manifest = storage.verify_archive(state["archive"], state["manifest_sha256"])
            storage.verify_source(source, manifest, cleaned=True)
        else:
            manifest = state["manifest"] if state else storage.inventory(source)
            if not state:
                manifest.update(mode=MODE, profile=smoke_profile.fingerprint(), omitted_images=sorted(IMAGES))
            if manifest.get("mode") != MODE:
                raise ValueError("cannot change archive mode on resume")
            storage.verify_source(source, manifest)
            content = storage.manifest_bytes(manifest)
            target = destination / f"{source.name}-{uuid.uuid4().hex}.tar.gz"
            temporary = target.with_suffix(".gz.partial")
            state = dict(schema=storage.SCHEMA, mode=MODE, complete=False, archive=str(target),
                         temporary=str(temporary), manifest=manifest,
                         manifest_sha256=hashlib.sha256(content).hexdigest())
            write_json(state_path, state)
            root = destination / "objects"
            root.mkdir(exist_ok=True)
            for row in manifest["entries"]:
                if row["type"] in ("file", "hardlink") and row["path"] not in IMAGES:
                    store(source, row, root)
            with tarfile.open(temporary, "w:gz", compresslevel=1) as archive:
                member = tarfile.TarInfo(storage.MANIFEST)
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            with temporary.open("rb") as stream:
                os.fsync(stream.fileno())
            storage.verify_archive(temporary, state["manifest_sha256"])
            storage.verify_source(source, manifest)
            os.replace(temporary, target)
            storage.sync_directory(destination)
            state["complete"] = True
            state.pop("manifest")
            write_json(state_path, state)
            storage.sync_directory(source)
        storage.cleanup_payload(source)
        state["cleaned"] = True
        write_json(state_path, state)
        storage.sync_directory(source)
        storage.credit(source)
        return state
