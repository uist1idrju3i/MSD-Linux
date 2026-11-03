#!/usr/bin/env python3
"""Classify changes that require a development-image build and Trivy scan."""

import argparse
import fnmatch
import re
import subprocess
import sys


PATH_PATTERNS = (
    "docker/msd-dev.Dockerfile",
    "docker/debian.sources",
    "docker/msd-dev",
    ".github/zizmor-requirements.txt",
    "docker/qemu-patches/**",
    "docker/qemu-signing-key.asc",
    ".github/workflows/publish-dev-image.yml",
)

COMMIT_PATTERN = re.compile(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}")


class ScopeError(RuntimeError):
    """Raised when the diff cannot be classified safely."""


def changed_paths(base_sha: str, head_sha: str, *, cwd: str | None = None) -> list[str]:
    for name, value in (("base", base_sha), ("head", head_sha)):
        if not COMMIT_PATTERN.fullmatch(value):
            raise ScopeError(f"Invalid {name} commit ID.")

    result = subprocess.run(
        ["git", "diff", "--no-renames", "--name-only", "-z", base_sha, head_sha],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise ScopeError(f"git diff failed with exit code {result.returncode}: {error}")

    return [
        path.decode("utf-8", errors="surrogateescape")
        for path in result.stdout.split(b"\0")
        if path
    ]


def requires_build(paths: list[str]) -> bool:
    return any(
        fnmatch.fnmatchcase(path, pattern)
        for path in paths
        for pattern in PATH_PATTERNS
    )


def needs_development_image(base_sha: str, head_sha: str, *, cwd: str | None = None) -> bool:
    return requires_build(changed_paths(base_sha, head_sha, cwd=cwd))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_sha")
    parser.add_argument("head_sha")
    args = parser.parse_args()

    try:
        changed = needs_development_image(args.base_sha, args.head_sha)
    except ScopeError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(str(changed).lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
