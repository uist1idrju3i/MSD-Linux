#!/usr/bin/env python3
"""Validate the release ledger against its assets, changelog, and local Git refs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re
import subprocess


HEADER = [
    "tag",
    "semver",
    "prerelease",
    "commit",
    "update_number",
    "signing_key",
    "release_url",
    "assets_sha256",
    "note",
]
TAG_RE = re.compile(
    r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-rc\.([1-9][0-9]*))?$"
)
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
NUMBER_RE = re.compile(r"^(0|[1-9][0-9]*)$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}  \S.*$")


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def version_key(match: re.Match[str]) -> tuple[int, int, int, int, int]:
    major, minor, patch, prerelease, rc_number = match.groups()
    return (
        int(major),
        int(minor),
        int(patch),
        0 if prerelease else 1,
        int(rc_number or 0),
    )


def check(root: Path, require_tags: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    csv_path = root / "docs/releases/releases.csv"
    rows: list[dict[str, str]] = []

    try:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != HEADER:
                errors.append(f"header mismatch in {csv_path}")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        errors.append(f"cannot read {csv_path}: {exc}")

    seen: dict[str, set[str]] = {
        "tag": set(),
        "commit": set(),
        "update_number": set(),
    }
    recorded_tags: set[str] = set()
    sortable: list[tuple[tuple[int, int, int, int, int], str, str]] = []
    previous_number: int | None = None
    changelog_path = root / "CHANGELOG.md"
    try:
        changelog = changelog_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        changelog = ""
        errors.append(f"cannot read {changelog_path}: {exc}")

    for index, row in enumerate(rows, start=2):
        prefix = f"{csv_path}:{index}"
        tag = (row.get("tag") or "").strip()
        semver = (row.get("semver") or "").strip()
        prerelease = (row.get("prerelease") or "").strip()
        commit = (row.get("commit") or "").strip()
        number = (row.get("update_number") or "").strip()
        recorded_tags.add(tag)

        for field, value in (
            ("tag", tag),
            ("commit", commit),
            ("update_number", number),
        ):
            if value in seen[field]:
                errors.append(f"{prefix}: duplicate {field} {value!r}")
            seen[field].add(value)

        match = TAG_RE.fullmatch(tag)
        if not match:
            errors.append(f"{prefix}: invalid tag {tag!r}")
        if semver != tag[1:]:
            errors.append(f"{prefix}: semver must equal tag without leading v")
        if match:
            sortable.append((version_key(match), number, tag))

        if prerelease not in {"true", "false"}:
            errors.append(f"{prefix}: prerelease must be true or false")
        if match and match.group(4) and prerelease == "false":
            errors.append(f"{prefix}: rc tag cannot have prerelease=false")
        if not COMMIT_RE.fullmatch(commit):
            errors.append(f"{prefix}: commit must be 40 lowercase hexadecimal characters")
        if not NUMBER_RE.fullmatch(number):
            errors.append(f"{prefix}: update_number must be decimal without leading zero")
        elif len(number) > 18:
            errors.append(f"{prefix}: update_number must have at most 18 digits")

        if semver and not re.search(
            rf"^## \[{re.escape(semver)}\](?:\s|$)", changelog, flags=re.MULTILINE
        ):
            errors.append(f"{prefix}: CHANGELOG.md has no ## [{semver}] heading")

        digest_name = (row.get("assets_sha256") or "").strip()
        digest_path = root / digest_name
        try:
            digest_lines = digest_path.read_text(encoding="utf-8").splitlines()
            if not digest_lines:
                errors.append(f"{prefix}: empty asset checksum file {digest_name!r}")
            for line_number, line in enumerate(digest_lines, start=1):
                if not DIGEST_RE.fullmatch(line):
                    errors.append(
                        f"{prefix}: malformed checksum line {line_number} in {digest_name!r}"
                    )
        except (OSError, UnicodeError) as exc:
            errors.append(f"{prefix}: cannot read asset checksum file {digest_name!r}: {exc}")

        if COMMIT_RE.fullmatch(commit):
            object_exists = git(root, "cat-file", "-e", f"{commit}^{{commit}}").returncode == 0
            if not object_exists:
                message = f"{prefix}: commit object {commit} is missing locally"
                (errors if require_tags else warnings).append(message)
            else:
                result = git(root, "show", "-s", "--format=%ct", commit)
                if result.returncode != 0:
                    errors.append(f"{prefix}: cannot read commit %ct for {commit}")
                elif NUMBER_RE.fullmatch(result.stdout.strip()):
                    if result.stdout.strip() != number:
                        errors.append(f"{prefix}: update_number does not match commit %ct")

        if match:
            ref = f"refs/tags/{tag}"
            exists = git(root, "show-ref", "--verify", "--quiet", ref).returncode == 0
            if not exists:
                message = f"{prefix}: tag {tag} is missing locally"
                (errors if require_tags else warnings).append(message)
            else:
                result = git(root, "rev-parse", "--verify", f"{ref}^{{commit}}")
                if result.returncode != 0:
                    errors.append(f"{prefix}: local tag {tag} does not peel to a commit")
                elif COMMIT_RE.fullmatch(commit):
                    if result.stdout.strip() != commit:
                        errors.append(f"{prefix}: local tag {tag} points to a different commit")

    for _, number, tag in sorted(sortable, key=lambda entry: entry[0]):
        if not NUMBER_RE.fullmatch(number):
            continue
        if previous_number is not None and int(number) <= previous_number:
            errors.append(f"update_number is not strictly increasing in SemVer order at {tag}")
        previous_number = int(number)

    if require_tags:
        result = git(root, "tag", "--list")
        if result.returncode != 0:
            errors.append("cannot list local Git tags")
        else:
            for tag in result.stdout.splitlines():
                if tag.startswith("v") and not TAG_RE.fullmatch(tag):
                    errors.append(f"invalid local v* tag {tag!r}")
                elif TAG_RE.fullmatch(tag) and tag not in recorded_tags:
                    errors.append(f"unrecorded local tag {tag!r}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-tags", action="store_true")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root containing CHANGELOG.md and docs/releases/releases.csv",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    errors, warnings = check(root, args.require_tags)
    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}")
    print(f"Summary: errors={len(errors)} warnings={len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
