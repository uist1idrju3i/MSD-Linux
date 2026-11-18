#!/usr/bin/env python3
"""Capacity reservations, bounded logs, and verified attempt archives."""

import argparse
import csv
import errno
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import time
import uuid

from supervisor import finalize, load_json, matrix_ok, published, write_json


GIB = 1024 ** 3
SCHEMA = "fs-compare-v2-storage/1"
MANIFEST = "_fs_compare_manifest.json"
STATE = ".storage.json"


def positive(value):
    number = int(value)
    if number < 1:
        raise ValueError("storage limits must be positive")
    return number


def nonnegative(value):
    number = int(value)
    if number < 0:
        raise ValueError("negative attempt count")
    return number


def log_limit():
    if os.environ.get("FSCMP_SMOKE") == "1":
        import smoke_profile
        return smoke_profile.load()["log_limit"]
    return positive(os.environ.get("FSCMP_LOG_LIMIT_BYTES", 256 * 1024 ** 2))


def digest(stream):
    result = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        result.update(block)
    return result.hexdigest()


def persistent(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("persistent absolute path required")
    path = path.resolve()
    if any(path == root or root in path.parents for root in
                                     map(Path, ("/tmp", "/var/tmp", "/run", "/dev/shm"))):
        raise ValueError("archive and capacity paths must be persistent absolute paths")
    return path


def archive_root(source):
    return persistent(os.environ.get("FSCMP_ARCHIVE_DIR", str(Path(source).parent / "archives")))


def unpacked_size(output, runner=subprocess.run):
    output = Path(output)
    result = runner([str(output / "host/bin/unsquashfs"), "-lln",
                     str(output / "images/rootfs.squashfs")],
                    capture_output=True, text=True, check=True)
    size = count = 0
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 3 or len(fields[0]) != 10 or fields[0][0] not in "dl-bcp":
            continue
        count += 1
        if fields[0][0] == "-":
            size += int(fields[2])
    if not count:
        raise ValueError("cannot estimate unpacked rootfs from unsquashfs listing")
    return size + count * 65536


def nearest(path):
    path = Path(path).resolve()
    while not path.exists():
        path = path.parent
    return path


def filesystem(path):
    path = nearest(path)
    info = path.stat()
    space = os.statvfs(path)
    return str(info.st_dev), space.f_bavail * space.f_frsize


def estimate(paths, jobs, attempts, rootfs, limit, probe=None, smoke=0):
    probe = probe or filesystem
    jobs, rootfs, limit = map(positive, (jobs, rootfs, limit))
    attempts = nonnegative(attempts)
    active = min(jobs, attempts)
    payload = 8 * GIB + 2 * rootfs + GIB + limit
    amounts = {
        "output": active * (8 * GIB + 2 * rootfs + GIB) + attempts * (limit + rootfs),
        "temp": active * (8 * GIB + rootfs),
        # No sparse, compression, or reflink savings are assumed.
        "archive": attempts * (payload * 11 // 10 + 16 * 1024 ** 2),
    }
    if smoke:
        import smoke_profile
        smoke = nonnegative(smoke)
        if smoke > attempts:
            raise ValueError("smoke count exceeds attempts")
        main = attempts - smoke
        metadata = 16 * 1024 ** 2
        light = smoke_profile.load()["log_limit"] + metadata
        amounts["output"] = active * (8 * GIB + 2 * rootfs + GIB) + main * (limit + rootfs) + smoke * light
        amounts["archive"] = main * (payload * 11 // 10 + 16 * 1024 ** 2) + smoke * light + 2 * rootfs + GIB
    groups = {}
    for role, path in paths.items():
        device, free = probe(path)
        group = groups.setdefault(device, dict(estimate=0, free=free, paths={}))
        group["estimate"] += amounts[role]
        group["free"] = min(group["free"], free)
        group["paths"][role] = str(path)
    for group in groups.values():
        group["required"] = max((group["estimate"] * 6 + 4) // 5, 5 * GIB)
    return groups


def capacity(path, initialize=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        model = initialize if initialize is not None else load_json(path)
        remaining = max(0, model["attempts"] - len(model["completed"]))
        model["remaining_attempts"] = remaining
        model["filesystems"] = estimate(model["paths"], model["jobs"], remaining,
                                        model["rootfs"], model["log_limit"],
                                        smoke=max(0, model.get("counts", {}).get("smoke_probes", 0)
                                                  - len(model.get("completed_smoke", []))))
        write_json(path, model)
        if any(group["free"] < group["required"] for group in model["filesystems"].values()):
            raise OSError(errno.ENOSPC, f"capacity estimate exceeds free space; see {path}")
    return model


def prepare(directory, output, attempts, counts=None):
    directory = Path(directory).resolve()
    destination = archive_root(directory)
    os.environ["FSCMP_ARCHIVE_DIR"] = str(destination)
    path = Path(os.environ.get("FSCMP_CAPACITY_FILE", directory / "capacity.json"))
    jobs = positive(os.environ.get("FSCMP_JOBS", "1"))
    model = dict(schema=SCHEMA, paths=dict(output=str(directory.parent),
                 temp=str(Path(os.environ.get("TMPDIR", "/tmp")).resolve()),
                 archive=str(destination)), jobs=jobs, attempts=nonnegative(attempts),
                 rootfs=unpacked_size(output), log_limit=log_limit(), completed=[], counts=counts or {})
    capacity(path, model)
    os.environ["FSCMP_CAPACITY_FILE"] = str(path)
    return path


def remaining_attempts(rows, matrix, maximum):
    matrix = Path(matrix)
    summary = matrix / "matrix-summary.csv"
    with summary.open() if summary.exists() else io.StringIO("") as stream:
        recorded = list(csv.DictReader(stream))
    remaining = 0
    for config, test, repetition in rows:
        failures = {row["run_id"] for row in recorded
                    if (row.get("config"), row.get("test"), row.get("repetition")) ==
                    (config, test, repetition) and row.get("status") != "ok"}
        success = False
        prefix = f"{matrix.name}-{test}-{config}-r{repetition}-"
        for source in matrix.parent.glob(prefix + "*"):
            if not source.is_dir():
                continue
            try:
                state = load_json(source / STATE)
                if not state.get("complete") or not state.get("cleaned"):
                    continue
                manifest = verify_archive(state["archive"], state["manifest_sha256"])
                verify_source(source, manifest, cleaned=True)
                result = published(source / "summary.csv")
                if result and matrix_ok(source / "summary.csv", 0):
                    success = True
                elif result and result["status"] != "ok":
                    failures.add(source.name)
            except (OSError, ValueError, KeyError, tarfile.TarError):
                continue
        if not success:
            remaining += max(0, maximum - len(failures))
    return remaining


def check_capacity():
    if os.environ.get("FSCMP_CAPACITY_FILE"):
        capacity(os.environ["FSCMP_CAPACITY_FILE"])


def credit(source):
    if not os.environ.get("FSCMP_CAPACITY_FILE"):
        return
    path = Path(os.environ["FSCMP_CAPACITY_FILE"])
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        model = load_json(path)
        name = str(Path(source).resolve())
        if name not in model["completed"]:
            model["completed"].append(name)
            if os.environ.get("FSCMP_SMOKE") == "1":
                model.setdefault("completed_smoke", []).append(name)
            write_json(path, model)


def logs_over_limit(source, limit, extra=None):
    paths = [path for pattern in ("*.log", "*.jsonl", "errors.txt") for path in Path(source).rglob(pattern)
             if not path.is_symlink() and "rootfs" not in path.relative_to(source).parts]
    if extra and Path(extra).is_file():
        paths.append(Path(extra))
    sizes = {str(path): path.stat().st_size for path in paths if path.is_file()}
    return dict(limit=limit, total=sum(sizes.values()), files=sizes) if sum(sizes.values()) > limit else None


def watch(source, parent):
    signal.signal(signal.SIGTERM, lambda *_args: sys.exit(0))
    while True:
        violation = logs_over_limit(source, log_limit(), os.environ.get("FSCMP_LAUNCH_LOG"))
        if violation:
            write_json(Path(source) / "log-limit.json", violation)
            os.kill(parent, signal.SIGTERM)
            return
        os.kill(parent, 0)
        time.sleep(0.2)


def run_child(command, environment, log):
    try:
        process = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT)
    except OSError as error:
        log.write(f"launcher failed: {error}\n")
        return subprocess.CompletedProcess(command, 127)
    handlers = {number: signal.signal(number, lambda number, _frame: process.send_signal(number)
                                      if process.poll() is None else None)
                for number in (signal.SIGTERM, signal.SIGINT)}
    try:
        return subprocess.CompletedProcess(command, process.wait())
    finally:
        for number, handler in handlers.items():
            signal.signal(number, handler)
        if process.poll() is None:
            process.terminate()
            process.wait()


def canonical_paths(paths):
    return sorted(paths, key=lambda path: Path(path).parts)


def inventory(source):
    source = Path(source)
    entries = []
    inodes = {}
    for path in canonical_paths(source.rglob("*")):
        relative = path.relative_to(source).as_posix()
        if relative == STATE:
            continue
        if relative == MANIFEST:
            raise ValueError("reserved archive manifest name in source")
        info = path.lstat()
        mode = info.st_mode
        kind = next((name for name, predicate in (
            ("file", stat.S_ISREG), ("directory", stat.S_ISDIR), ("symlink", stat.S_ISLNK),
            ("character", stat.S_ISCHR), ("block", stat.S_ISBLK), ("fifo", stat.S_ISFIFO))
                     if predicate(mode)), None)
        if kind is None:
            raise ValueError(f"unsupported source type: {relative}")
        target = os.readlink(path) if kind == "symlink" else ""
        if kind == "file":
            with path.open("rb") as stream:
                value = digest(stream)
            inode = (info.st_dev, info.st_ino)
            if inode in inodes:
                kind, target = "hardlink", inodes[inode]
            else:
                inodes[inode] = relative
        else:
            value = hashlib.sha256(os.fsencode(target)).hexdigest()
        entries.append(dict(path=relative, type=kind, sha256=value,
                            size=info.st_size if kind in ("file", "hardlink", "symlink") else 0,
                            mtime_ns=info.st_mtime_ns, link=target,
                            mode=stat.S_IMODE(mode), device=info.st_rdev))
    return dict(schema=SCHEMA, entries=entries)


def manifest_bytes(manifest):
    return json.dumps(manifest, sort_keys=True).encode()


def verify_archive(path, expected=None):
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)) or names.count(MANIFEST) != 1:
            raise ValueError("duplicate or missing archive member")
        content = archive.extractfile(MANIFEST).read()
        if expected and hashlib.sha256(content).hexdigest() != expected:
            raise ValueError("archive manifest hash mismatch")
        manifest = json.loads(content)
        if manifest.get("mode"):
            import smoke_storage
            return smoke_storage.verify(path, archive, manifest)
        if manifest["schema"] != SCHEMA or set(names) != {MANIFEST, *(row["path"] for row in manifest["entries"])}:
            raise ValueError("archive member set mismatch")
        types = {"file": tarfile.REGTYPE, "hardlink": tarfile.LNKTYPE,
                 "directory": tarfile.DIRTYPE, "symlink": tarfile.SYMTYPE,
                 "character": tarfile.CHRTYPE, "block": tarfile.BLKTYPE, "fifo": tarfile.FIFOTYPE}
        for row in manifest["entries"]:
            member = archive.getmember(row["path"])
            if member.islnk():
                target = archive.getmember(row["link"])
                if not target.isfile():
                    raise ValueError("hardlink target must be a regular member")
                size = target.size
            else:
                size = member.size if member.isfile() else len(os.fsencode(member.linkname))
            if (member.type != types[row["type"]]
                    or member.pax_headers.get("FSCMP.mtime_ns") != str(row["mtime_ns"])
                    or member.mode != row["mode"] or member.linkname != row["link"]
                    or (row["type"] in ("character", "block")
                        and os.makedev(member.devmajor, member.devminor) != row["device"])
                    or size != row["size"]):
                raise ValueError(f"archive metadata mismatch: {row['path']}")
            value = (digest(archive.extractfile(member)) if member.isfile() or member.islnk()
                     else hashlib.sha256(os.fsencode(member.linkname)).hexdigest())
            if value != row["sha256"]:
                raise ValueError(f"archive payload mismatch: {row['path']}")
    return manifest


def verify_source(source, manifest, cleaned=False):
    current = inventory(source)
    expected = {row["path"]: row for row in manifest["entries"]}
    actual = {row["path"]: row for row in current["entries"]}
    if cleaned:
        surviving = {}
        for name in canonical_paths(actual):
            row = expected.get(name)
            if row and row["type"] in ("file", "hardlink"):
                original = row["link"] if row["type"] == "hardlink" else name
                target = surviving.setdefault(original, name)
                expected[name] = dict(row, type="file" if name == target else "hardlink",
                                      link="" if name == target else target)
    for name, row in actual.items():
        original = expected.get(name)
        if cleaned and row["type"] == "directory" and (name == "build" or name.startswith("build/")):
            original = dict(original, mtime_ns=row["mtime_ns"]) if original else None
        if original != row:
            raise ValueError("archive source changed")
    missing = expected.keys() - actual.keys()
    if missing and (not cleaned or any(name != "sdcard.img" and name != "build"
                                      and not name.startswith("build/") for name in missing)
                    or any(is_log(name) for name in missing)):
        raise ValueError("archive source disappeared")


def is_log(path):
    return Path(path).suffix in (".log", ".jsonl", ".txt")


def cleanup_payload(source):
    build = source / "build"
    if build.is_symlink():
        raise ValueError("refusing symlink build cleanup")
    if build.exists():
        for path in sorted(build.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            if path.is_dir() and not path.is_symlink():
                if not any(path.iterdir()):
                    path.rmdir()
            elif not is_log(path):
                path.unlink()
    (source / "sdcard.img").unlink(missing_ok=True)


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def archive_attempt(source, destination):
    state_path = Path(source) / STATE
    state = load_json(state_path) if state_path.exists() else {}
    if os.environ.get("FSCMP_SMOKE") == "1" or state.get("mode"):
        import smoke_storage
        return smoke_storage.archive_attempt(source, destination)
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or source in destination.parents:
        raise ValueError("archive destination must be outside the source")
    destination.mkdir(parents=True, exist_ok=True)
    lock_name = hashlib.sha256(os.fsencode(source)).hexdigest()
    with (destination / f".{lock_name}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state_path = source / STATE
        state = load_json(state_path) if state_path.exists() else None
        if state and state.get("complete"):
            manifest = verify_archive(state["archive"], state["manifest_sha256"])
            verify_source(source, manifest, cleaned=True)
        else:
            manifest = state["manifest"] if state else inventory(source)
            verify_source(source, manifest)
            content = manifest_bytes(manifest)
            target = destination / f"{source.name}-{uuid.uuid4().hex}.tar.gz"
            temporary = target.with_suffix(target.suffix + ".partial")
            state = dict(schema=SCHEMA, complete=False, archive=str(target),
                         temporary=str(temporary), manifest=manifest,
                         manifest_sha256=hashlib.sha256(content).hexdigest())
            write_json(state_path, state)
            with tarfile.open(temporary, "w:gz", compresslevel=1, format=tarfile.PAX_FORMAT) as archive:
                for row in manifest["entries"]:
                    path = source / row["path"]
                    member = archive.gettarinfo(str(path), arcname=row["path"])
                    if row["type"] == "file":
                        member.type = tarfile.REGTYPE
                        member.linkname = ""
                        member.size = row["size"]
                    elif row["type"] == "hardlink":
                        member.type = tarfile.LNKTYPE
                        member.linkname = row["link"]
                        member.size = 0
                    member.pax_headers["FSCMP.mtime_ns"] = str(row["mtime_ns"])
                    if member.isfile():
                        with path.open("rb") as stream:
                            archive.addfile(member, stream)
                    else:
                        archive.addfile(member)
                member = tarfile.TarInfo(MANIFEST)
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            with temporary.open("rb") as stream:
                os.fsync(stream.fileno())
            verify_archive(temporary, state["manifest_sha256"])
            verify_source(source, manifest)
            os.replace(temporary, target)
            sync_directory(destination)
            state["complete"] = True
            state.pop("manifest")
            write_json(state_path, state)
            sync_directory(source)
        # Raw logs and final results are never removed.
        cleanup_payload(source)
        state["cleaned"] = True
        write_json(state_path, state)
        sync_directory(source)
        credit(source)
        return state


def finish(source, test, status, launcher=None):
    source = Path(source)
    source.mkdir(exist_ok=True)
    if not (source / STATE).exists():
        if launcher and Path(launcher).is_file():
            shutil.copy2(launcher, source / "launcher.log")
        violation = logs_over_limit(source, log_limit())
        if violation or (source / "log-limit.json").exists():
            if violation:
                write_json(source / "log-limit.json", violation)
            status = status or 1
        for phase in ("run", "verify"):
            log = source / f"qemu-{phase}.log"
            result = source / f"phase-{phase}.json"
            if log.exists() and (not result.exists() or load_json(result).get("reaped") is not True):
                raise ValueError("QEMU not proven reaped; no archive or cleanup")
        finalize(source, test, status, rescan=True)
        violation = logs_over_limit(source, log_limit())
        if violation and not (source / "log-limit.json").exists():
            write_json(source / "log-limit.json", violation)
            finalize(source, test, status or 1, rescan=True)
    return archive_attempt(source, archive_root(source))


def context(source, config, test, run_id, points):
    source = Path(source)
    evidence = source / "evidence"
    evidence.mkdir()
    harness = evidence / "harness"
    harness.mkdir()
    here = Path(__file__).parent
    env = load_json(os.environ["FSCMP_ENVIRONMENT_FILE"])
    for path in [*here.iterdir(),
                 here.parents[4] / "board/cardputerzero/qemu/run-qemu.sh"]:
        if path.is_file():
            shutil.copy2(path, harness / path.name)
            with (harness / path.name).open("rb") as stream:
                if digest(stream) != env["files"][str(path)]:
                    raise ValueError("harness changed after preflight")
    for key in ("FSCMP_ENVIRONMENT_FILE", "FSCMP_PLAN_FILE", "FSCMP_CAPACITY_FILE"):
        if os.environ.get(key):
            shutil.copy2(os.environ[key], evidence / Path(os.environ[key]).name)
    if os.environ.get("FSCMP_ENVIRONMENT_FILE"):
        configs = evidence / "configs"
        configs.mkdir()
        for name, expected in env["files"].items():
            path = Path(name)
            if path.name not in (".config", "kernel.release"):
                continue
            target = configs / (hashlib.sha256(os.fsencode(path)).hexdigest() + path.name)
            shutil.copy2(path, target)
            with target.open("rb") as stream:
                if digest(stream) != expected:
                    raise ValueError("generated config changed after preflight")
    write_json(evidence / "storage-settings.json",
               dict(log_limit=log_limit(), archive=str(archive_root(source))))
    write_json(evidence / "command.json",
               dict(command=[str(here / "fs-compare.sh"), config, test, run_id,
                             *(["--points", points] if points else [])]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("check")
    watcher = sub.add_parser("watch")
    watcher.add_argument("source", type=Path)
    watcher.add_argument("parent", type=int)
    capture = sub.add_parser("context")
    capture.add_argument("source", type=Path)
    for name in ("config", "test", "run_id", "points"):
        capture.add_argument(name)
    done = sub.add_parser("finish")
    done.add_argument("source", type=Path)
    done.add_argument("test")
    done.add_argument("status", type=int)
    done.add_argument("--launcher", type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("source", type=Path)
    args = parser.parse_args()
    if args.action == "check":
        check_capacity()
    elif args.action == "watch":
        watch(args.source, args.parent)
    elif args.action == "context":
        context(args.source, args.config, args.test, args.run_id, args.points)
    elif args.action == "finish":
        finish(args.source, args.test, args.status, args.launcher)
    else:
        state = load_json(args.source / STATE)
        if state.get("complete") is not True:
            raise ValueError("incomplete archive; source retained")
        manifest = verify_archive(state["archive"], state["manifest_sha256"])
        verify_source(args.source, manifest, cleaned=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, tarfile.TarError, subprocess.SubprocessError) as error:
        print(f"fs-compare-storage: {error}", file=sys.stderr)
        sys.exit(1)
