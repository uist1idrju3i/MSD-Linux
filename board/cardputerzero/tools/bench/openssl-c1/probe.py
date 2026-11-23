#!/usr/bin/env python3
"""Record C1 endpoint handshakes, A/A and a hostname negative control."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[5]
HOSTS = ("github.com", "api.github.com", "codeload.github.com",
         "objects.githubusercontent.com", "release-assets.githubusercontent.com", "muromi.moe")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def outcome(code, output, protocol, negative):
    if negative:
        return code not in (0, "timeout") and "hostname mismatch" in output
    return (code == 0 and f"Protocol version: TLSv{protocol}" in output
            and "Verification: OK" in output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.relative_to(ROOT)
    original = args.reference.read_bytes()
    out.mkdir(parents=True, exist_ok=False)
    for variant in ("C0", "C0-AA", "C1"):
        config = out / f"{variant}.cnf"
        config.write_bytes(original)
        if variant == "C1":
            subprocess.run([sys.executable, str(ROOT / "board/cardputerzero/tools/openssl-c1.py"),
                            str(config)], check=True)
    metadata = {
        "utc": datetime.now(timezone.utc).isoformat(), "host": platform.platform(),
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "openssl_version": subprocess.check_output(["openssl", "version", "-a"], text=True),
        "openssl_sha256": sha(Path(shutil.which("openssl")).resolve()),
        "runner_sha256": sha(__file__),
        "policy_sha256": sha(ROOT / "board/cardputerzero/tools/openssl-c1.py"),
        "configs": {name: sha(out / f"{name}.cnf") for name in ("C0", "C0-AA", "C1")},
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    cases = [("C0", "github.com", 443, "1.3", False), ("C0-AA", "github.com", 443, "1.3", False),
             ("C1", "github.com", 443, "1.3", True)]
    cases += [("C1", host, 443, protocol, False) for host in HOSTS for protocol in ("1.2", "1.3")]
    cases.append(("C1", "time.cloudflare.com", 4460, "1.3", False))
    passed = True
    with (out / "results.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=(
            "case", "variant", "host", "port", "protocol", "negative", "exit_code", "pass", "log_sha256"))
        writer.writeheader()
        for index, (variant, host, port, protocol, negative) in enumerate(cases, 1):
            config = out / f"{variant}.cnf"
            command = ["openssl", "s_client", "-connect", f"{host}:{port}", "-servername", host,
                       "-" + "tls" + protocol.replace(".", "_"), "-brief", "-verify_return_error",
                       "-verify_hostname", "wrong.invalid" if negative else host]
            if port == 4460:
                command += ["-alpn", "ntske/1"]
            env = dict(os.environ, OPENSSL_CONF=str(config))
            try:
                result = subprocess.run(command, input="", text=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, timeout=25, env=env)
                code, output = result.returncode, result.stdout
            except subprocess.TimeoutExpired as error:
                code, output = "timeout", error.stdout or b""
                if isinstance(output, bytes):
                    output = output.decode(errors="replace")
            log = out / f"{index:02d}.log"
            log.write_text(f"OPENSSL_CONF={config.relative_to(ROOT)}\n$ {' '.join(command)}\n"
                           + output + f"\nEXIT={code}\n")
            ok = outcome(code, output, protocol, negative)
            passed &= ok
            writer.writerow(dict(case=index, variant=variant, host=host, port=port, protocol=protocol,
                                 negative=int(negative), exit_code=code, **{"pass": int(ok)},
                                 log_sha256=sha(log)))
            stream.flush()
            print(f"case={index} {variant} {host} TLS{protocol} negative={int(negative)} "
                  f"exit={code} pass={int(ok)}", flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
