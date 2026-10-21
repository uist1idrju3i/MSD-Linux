#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent


def main():
    default_root = os.environ.get("PPD_PATHMAP_ROOT", str(SCRIPT_DIR / "inputs"))
    default_out = os.environ.get(
        "PPD_PATHMAP_OUT", str(Path(default_root) / "rodata-residual")
    )
    parser = argparse.ArgumentParser(
        description="Run the PPD path-map residual analysis scripts."
    )
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--out", type=Path, default=default_out)
    args = parser.parse_args()

    root = args.root.resolve()
    out = args.out.resolve()
    if not root.is_dir():
        parser.error(f"input root does not exist: {root}")
    out.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PPD_PATHMAP_ROOT"] = str(root)
    env["PPD_PATHMAP_OUT"] = str(out)
    for name in ("analyze_residuals.py", "trace_references.py"):
        subprocess.run(
            [sys.executable, str(SCRIPT_DIR / name)],
            check=True,
            env=env,
        )


if __name__ == "__main__":
    main()
