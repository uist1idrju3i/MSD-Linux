#!/usr/bin/env python3
"""Record one TLS probe per host and group list without rewriting output."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess


HOSTS = ["github.com", "api.github.com", "codeload.github.com",
         "objects.githubusercontent.com", "release-assets.githubusercontent.com", "muromi.moe"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with args.out.open("x") as log:
        log.write(datetime.now(timezone.utc).isoformat() + "\n")
        log.write(subprocess.check_output(["openssl", "version", "-a"], text=True))
        for host in HOSTS:
            for group in ["X25519MLKEM768:X25519", "X25519MLKEM768"]:
                command = ["openssl", "s_client", "-connect", f"{host}:443", "-servername", host,
                           "-tls1_3", "-groups", group, "-brief"]
                log.write("$ " + " ".join(command) + "\n")
                log.flush()
                try:
                    result = subprocess.run(command, input="", text=True, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, timeout=25)
                    log.write(result.stdout)
                    log.write(f"EXIT={result.returncode}\n")
                except subprocess.TimeoutExpired as error:
                    output = error.stdout or b""
                    log.write(output.decode(errors="replace") if isinstance(output, bytes) else output)
                    log.write("EXIT=timeout\n")
                log.flush()


if __name__ == "__main__":
    main()
