#!/usr/bin/env python3
"""Save/load an exact-input local CI image; never authenticate a published image."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


FORMAT = 1
ARCHIVE = "image.tar"
METADATA = "image.json"
MAX_BYTES = 512 * 1024 * 1024


def docker(*arguments: str) -> str:
    return subprocess.check_output(["docker", *arguments], text=True).strip()


def inspect(image: str) -> dict[str, str]:
    template = '{"id":{{json .Id}},"os":{{json .Os}},"arch":{{json .Architecture}}}'
    result = json.loads(docker("image", "inspect", image, "--format", template))
    if not isinstance(result, dict) or set(result) != {"id", "os", "arch"}:
        raise ValueError("Invalid image identity")
    if not all(isinstance(value, str) for value in result.values()):
        raise ValueError("Invalid image identity fields")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", result["id"]):
        raise ValueError("Invalid image ID")
    return result


def platform() -> str:
    value = docker("version", "--format", "{{.Server.Os}}/{{.Server.Arch}}")
    if value not in {"linux/amd64", "linux/arm64"}:
        raise ValueError(f"Unsupported Docker platform: {value}")
    return value


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def report(source: str, size: int, cacheable: bool) -> None:
    values = {"source": source, "archive-bytes": str(size),
              "cacheable": str(cacheable).lower()}
    for name, value in values.items():
        print(f"=dev-image=\t{name}\t{value}")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a") as stream:
            stream.writelines(f"{key}={value}\n" for key, value in values.items())
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary).open("a") as stream:
            stream.write(f"\nDevelopment image: **{source}**; archive {size} bytes; "
                         f"cacheable: {str(cacheable).lower()}.\n")
            if not cacheable:
                stream.write("Cache save skipped: archive exceeds the configured size limit.\n")


def save(directory: Path, tag: str, image: str, max_bytes: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    archive = directory / ARCHIVE
    metadata = directory / METADATA
    for path in (archive, metadata):
        path.unlink(missing_ok=True)
    identity = inspect(image)
    if f'{identity["os"]}/{identity["arch"]}' != platform():
        raise ValueError("Cannot cache an image for a different Docker platform")
    subprocess.run(["docker", "save", "--output", str(archive), image], check=True)
    size = archive.stat().st_size
    if size > max_bytes:
        archive.unlink()
        print(f"Archive exceeds {max_bytes} bytes; skipping cache save.")
        report("local-build", size, False)
        return
    if size == 0:
        raise ValueError("Empty image archive")
    record = {"format": FORMAT, "tag": tag, "image": image, **identity,
              "bytes": size, "sha256": digest(archive)}
    metadata.write_text(json.dumps(record, sort_keys=True) + "\n")
    report("local-build", size, True)


def load(directory: Path, tag: str, image: str, max_bytes: int) -> None:
    archive = directory / ARCHIVE
    metadata = directory / METADATA
    for path in (archive, metadata):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing or unsafe cache file: {path.name}")
    if metadata.stat().st_size > 4096:
        raise ValueError("Oversized cache metadata")
    record = json.loads(metadata.read_text())
    fields = {"format", "tag", "image", "id", "os", "arch", "bytes", "sha256"}
    if not isinstance(record, dict) or set(record) != fields:
        raise ValueError("Invalid cache metadata fields")
    if type(record["format"]) is not int or record["format"] != FORMAT:
        raise ValueError("Unknown cache format")
    if record["tag"] != tag or record["image"] != image:
        raise ValueError("Cache inputs or image name do not match")
    if f'{record["os"]}/{record["arch"]}' != platform():
        raise ValueError("Cache platform does not match Docker")
    if not isinstance(record["id"], str) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", record["id"]):
        raise ValueError("Invalid cached image ID")
    size = archive.stat().st_size
    if not 0 < size <= max_bytes or type(record["bytes"]) is not int or record["bytes"] != size:
        raise ValueError("Cache archive size does not match")
    if record["sha256"] != digest(archive):
        raise ValueError("Cache archive checksum does not match")
    subprocess.run(["docker", "load", "--input", str(archive)], check=True)
    if inspect(image) != {name: record[name] for name in ("id", "os", "arch")}:
        raise ValueError("Loaded image identity does not match metadata")
    report("local-cache", size, True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("save", "load"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--image", default="msd-dev:local")
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    args = parser.parse_args()
    if not re.fullmatch(r"inputs-[0-9a-f]{16}", args.tag) or args.max_bytes <= 0:
        parser.error("Invalid input tag or archive limit")
    try:
        if args.operation == "save":
            save(args.directory, args.tag, args.image, args.max_bytes)
        else:
            load(args.directory, args.tag, args.image, args.max_bytes)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Development image cache failed: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
