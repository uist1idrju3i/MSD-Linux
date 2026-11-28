#!/usr/bin/env python3
"""Check that the required real-library suite cannot silently skip."""

import os
from pathlib import Path
import subprocess


script = Path(__file__).with_name("run.sh")
environment = {**os.environ, "MSD_TEST_CRYPTSETUP_INCLUDE": "/missing-msd-test-headers"}
for required, code, message in (
    ("1", 1, b"real libcryptsetup test is required but development header is missing"),
    ("invalid", 2, b"Invalid MSD_TEST_REQUIRE_CRYPTSETUP"),
):
    result = subprocess.run([str(script)], capture_output=True, timeout=5,
                            env={**environment, "MSD_TEST_REQUIRE_CRYPTSETUP": required})
    assert result.returncode == code and message in result.stderr
    assert b"SKIP" not in result.stdout + result.stderr
print("ok - real-library guard: missing headers fail when required, invalid mode rejected")
