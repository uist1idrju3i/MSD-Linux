#!/usr/bin/env python3
"""Versioned light-smoke parameters, shared by build, guest and evidence."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path

PATH = Path(__file__).with_name("smoke-profile.json")
FIELDS = {"w1_files": (2, 200), "w2_updates": (2, 100), "w3_records": (51, 1000),
          "w4_bytes": (65536, 33554432), "idle_seconds": (3, 600),
          "quiesce_polls": (3, 30), "t7_bytes": (268435456, 4294967296),
          "log_limit": (8388608, 268435456)}


def load(path=PATH):
    data = json.loads(Path(path).read_text())
    if (set(data) != {*FIELDS, "schema", "archive_mode"}
            or data["schema"] != "fs-compare-v2-light/1"
            or data["archive_mode"] != "shared-nonimage-sha256/1"):
        raise ValueError("unknown smoke profile or archive mode")
    for key, (low, high) in FIELDS.items():
        if type(data[key]) is not int or not low <= data[key] <= high:
            raise ValueError(f"invalid smoke profile field: {key}")
    return data


def fingerprint():
    load()
    return hashlib.sha256(PATH.read_bytes()).hexdigest()


def logical_bytes(data):
    return data["w1_files"] * 4096 + data["w2_updates"] * 2048 + data["w3_records"] * 128 + data["w4_bytes"]


@contextmanager
def context():
    previous = os.environ.get("FSCMP_SMOKE")
    os.environ["FSCMP_SMOKE"] = "1"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("FSCMP_SMOKE", None)
        else:
            os.environ["FSCMP_SMOKE"] = previous


def render(kind):
    data = load()
    if kind == "header":
        return "\n".join(f"#define SMOKE_{key.upper()} {value}U" for key, value in data.items()
                         if key in FIELDS) + "\n"
    values = {f"SMOKE_{key.upper()}": value for key, value in data.items() if key in FIELDS}
    values.update(SMOKE_PROFILE_SHA256=fingerprint(), SMOKE_LOGICAL_BYTES=logical_bytes(data))
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("header", "shell"))
    print(render(parser.parse_args().kind), end="")
