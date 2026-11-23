#!/usr/bin/env python3
"""Exercise real RAUC streaming metadata requests against a loopback fault server."""

import argparse
from collections import Counter
import csv
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import random
import re
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit


SCENARIOS = ("range", "redirect", "ignore-range", "expire-bytes", "expire-time",
             "rate-once", "rate-always", "drop-once", "drop-always", "bad-ca", "range-aa")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FaultServer(ThreadingHTTPServer):
    daemon_threads = False

    def __init__(self, payload, scenario):
        super().__init__(("127.0.0.1", 0), Handler)
        self.payload = payload
        self.scenario = scenario
        self.events = []
        self.started = time.monotonic()
        self.object_requests = 0
        self.delivered = 0
        self.lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        pass

    def do_GET(self):
        server = self.server
        with server.lock:
            event = {"at_seconds": time.monotonic() - server.started,
                     "path": self.path, "range": self.headers.get("Range"),
                     "status": None, "body_bytes": 0,
                     "client_port": self.client_address[1]}
            server.events.append(event)
            path = urlsplit(self.path).path
            scenario = server.scenario
            redirect = scenario in ("redirect", "expire-bytes", "expire-time")
            if redirect and path == "/download":
                self.respond(event, 302, b"", {
                    "Location": "/objects/bundle?se=local-test-only&sig=not-a-secret"})
                return
            server.object_requests += 1
            number = server.object_requests
            match = re.fullmatch(r"bytes=(\d+)-(\d+)", self.headers.get("Range", ""))
            if not match:
                self.respond(event, 416, b"explicit closed range required")
                return
            start, end = map(int, match.groups())
            end = min(end, len(server.payload) - 1)
            event.update(start=start, end=end)
            if scenario == "expire-bytes" and server.delivered >= 4:
                self.respond(event, 403, b"expired after 4 served bytes")
                return
            if scenario == "expire-time" and time.monotonic() - server.started >= 0.25:
                self.respond(event, 403, b"expired after 0.25 seconds")
                return
            if (scenario == "rate-once" and number == 2) or (
                    scenario == "rate-always" and number >= 2):
                self.respond(event, 429, b"rate limited", {"Retry-After": "3"})
                return
            if scenario == "ignore-range":
                self.respond(event, 200, server.payload)
                return
            body = server.payload[start:end + 1]
            headers = {"Content-Range": f"bytes {start}-{end}/{len(server.payload)}",
                       "Accept-Ranges": "bytes"}
            drop = (scenario == "drop-once" and number == 2) or (
                scenario == "drop-always" and number >= 2)
            if scenario == "expire-time" and number == 1:
                time.sleep(0.35)
            self.respond(event, 206, body, headers, drop=drop)

    def respond(self, event, status, body, headers=None, drop=False):
        event["status"] = status
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        sent = body[:max(1, len(body) // 2)] if drop else body
        try:
            while event["body_bytes"] < len(sent):
                offset = event["body_bytes"]
                count = self.connection.send(sent[offset:offset + 4096])
                if not count:
                    raise ConnectionResetError("socket stopped accepting body")
                event["body_bytes"] += count
                self.server.delivered += count
        except (BrokenPipeError, ConnectionResetError):
            event["write_interrupted"] = True
        event["done_seconds"] = time.monotonic() - self.server.started
        event["dropped"] = drop
        self.close_connection = True
        if drop:
            self.connection.shutdown(socket.SHUT_RDWR)


def command(argv, log, env):
    with log.open("x") as stream:
        result = subprocess.run([str(x) for x in argv], env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=60)
    if result.returncode:
        raise RuntimeError(f"{argv[0]} failed: {log}")


def prepare(host, run, env):
    openssl = host / "bin/openssl"
    rauc = host / "bin/rauc"
    private = run / "private"
    private.mkdir(mode=0o700)
    ca = run / "ca.pem"
    leaf = run / "release.pem"
    command([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
             "-subj", "/CN=RAUC-PoC-throwaway-CA", "-keyout", private / "ca.key",
             "-out", ca], run / "ca-generation.log", env)
    command([openssl, "req", "-new", "-newkey", "rsa:2048", "-nodes",
             "-subj", "/CN=RAUC-PoC-release", "-keyout", private / "release.key",
             "-out", run / "release.csr"], run / "release-request.log", env)
    extension = run / "extensions.conf"
    extension.write_text("basicConstraints=critical,CA:FALSE\n"
                         "keyUsage=critical,digitalSignature\nextendedKeyUsage=codeSigning\n")
    command([openssl, "x509", "-req", "-in", run / "release.csr", "-CA", ca,
             "-CAkey", private / "ca.key", "-CAcreateserial", "-days", "1",
             "-extfile", extension, "-out", leaf], run / "release-sign.log", env)
    command([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
             "-subj", "/CN=RAUC-PoC-wrong-CA", "-keyout", private / "wrong.key",
             "-out", run / "wrong-ca.pem"], run / "wrong-ca-generation.log", env)
    content = run / "content"
    content.mkdir()
    rng = random.Random(20261123)
    for name, size in (("boot.img", 262144), ("rootfs.img", 524288)):
        (content / name).write_bytes(rng.randbytes(size))
    (content / "manifest.raucm").write_text(
        "[update]\ncompatible=rauc-streaming-poc\nversion=1.0.0\n"
        "[bundle]\nformat=verity\n"
        "[image.boot]\nfilename=boot.img\ntype=raw\nadaptive=block-hash-index\n"
        "[image.rootfs]\nfilename=rootfs.img\ntype=raw\nadaptive=block-hash-index\n")
    bundle = run / "test.raucb"
    command([rauc, "bundle", "--cert", leaf, "--key", private / "release.key",
             "--mksquashfs-args=-processors 2", content, bundle],
            run / "bundle-create.log", env)
    slots = run / "slots"
    slots.mkdir()
    for name in ("boot-a", "boot-b", "root-a", "root-b"):
        (slots / name).write_bytes(bytes(1048576))
    (slots / "autoboot.txt").write_text("poc-primary=A\n")
    (slots / "bootstate").write_text("poc-primary=A\n")
    backend = run / "backend.sh"
    backend.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\" >> '" + str(run / "backend-calls.log")
                       + "'\ncase \"$1\" in\nget-primary|get-current) echo A;;\n"
                       "get-state) echo good;;\n*) exit 1;;\nesac\n")
    backend.chmod(0o700)
    conf = run / "system.conf"
    conf.write_text(
        "[system]\ncompatible=rauc-streaming-poc\nbootloader=custom\n"
        "bundle-formats=verity\nactivate-installed=false\n"
        f"mountprefix={run}/mount\n[keyring]\npath={ca}\ncheck-purpose=codesign-rauc\n"
        f"[handlers]\nbootloader-custom-backend={backend}\n"
        f"[slot.rootfs.0]\ndevice={slots}/root-a\ntype=raw\nbootname=A\n"
        f"[slot.rootfs.1]\ndevice={slots}/root-b\ntype=raw\nbootname=B\n"
        f"[slot.boot.0]\ndevice={slots}/boot-a\ntype=raw\nparent=rootfs.0\n"
        f"[slot.boot.1]\ndevice={slots}/boot-b\ntype=raw\nparent=rootfs.1\n")
    return bundle, conf, slots


def execute(host, run, repeats, scenarios):
    env = dict(os.environ, PATH=f"{host}/bin:{host}/sbin:" + os.environ["PATH"],
               RAUC_CURL_VERBOSE="1")
    bundle, conf, slots = prepare(host, run, env)
    before = {p.name: digest(p) for p in slots.iterdir()}
    records = []
    payload = bundle.read_bytes()
    for scenario in scenarios:
        for repetition in range(1, repeats + 1):
            case = "range" if scenario == "range-aa" else scenario
            directory = run / f"{scenario}-{repetition:02}"
            directory.mkdir()
            with FaultServer(payload, case) as server:
                thread = threading.Thread(target=server.serve_forever)
                thread.start()
                argv = [str(host / "bin/rauc"), "--conf", str(conf), "info",
                        "--keyring", str(run / ("wrong-ca.pem" if case == "bad-ca" else "ca.pem")),
                        f"http://127.0.0.1:{server.server_port}/download"]
                start = time.monotonic()
                try:
                    result = subprocess.run(argv, env=env, text=True, capture_output=True, timeout=40)
                    status, stdout, stderr = result.returncode, result.stdout, result.stderr
                except subprocess.TimeoutExpired as error:
                    status = 124
                    stdout = (error.stdout or b"").decode()
                    stderr = (error.stderr or b"").decode()
                finally:
                    server.shutdown()
                    thread.join()
                seconds = time.monotonic() - start
            (directory / "stdout.log").write_text(stdout)
            (directory / "stderr.log").write_text(stderr)
            (directory / "requests.json").write_text(json.dumps(server.events, indent=2) + "\n")
            after = {p.name: digest(p) for p in slots.iterdir()}
            assert after == before, "info changed slot/state content"
            calls_file = run / "backend-calls.log"
            calls = calls_file.read_text().splitlines() if calls_file.exists() else []
            activation = sum(s.startswith(("set-primary", "set-state")) for s in calls)
            assert activation == 0, calls
            requests = [e for e in server.events if e["status"] != 302]
            ranges = Counter(e["range"] for e in requests)
            retry = sum(count - 1 for count in ranges.values())
            expect_success = case in ("range", "redirect", "rate-once", "drop-once")
            record = {
                "scenario": scenario, "repetition": repetition, "exit_status": status,
                "seconds": round(seconds, 6), "bundle_bytes": len(payload),
                "http_requests": len(server.events),
                "http_statuses": ",".join(str(e["status"]) for e in server.events),
                "body_bytes": sum(e["body_bytes"] for e in server.events),
                "range_retries": retry, "redirects": sum(e["status"] == 302 for e in server.events),
                "activation_calls": activation, "slot_state_hashes_unchanged": after == before,
                "expected_success": expect_success,
                "expected_exit_match": (status == 0) == expect_success and status != 124,
                "rauc_retry_messages": stderr.count("(retrying "),
            }
            downloaded = re.search(r"nbd dl_size: count=\d+ sum=([0-9.]+)", stderr)
            record["rauc_body_bytes"] = int(float(downloaded[1])) if downloaded else ""
            (directory / "result.json").write_text(json.dumps(
                dict(record, command=argv, hashes_before=before, hashes_after=after), indent=2) + "\n")
            records.append(record)
            print(json.dumps(record), flush=True)
    with (run / "results.csv").open("x") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    metadata = {
        "rauc_version": subprocess.check_output([str(host / "bin/rauc"), "--version"], text=True).strip(),
        "rauc_sha256": digest(host / "bin/rauc"), "bundle_sha256": digest(bundle),
        "script_sha256": digest(Path(__file__)), "file_slot_limits": "info only, no install",
        "private_keys_excluded_from_evidence": True, "repetitions": repeats,
        "scenarios": scenarios}
    (run / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--scenarios", nargs="+", choices=SCENARIOS, default=SCENARIOS,
                        help="conditions to run (default: all)")
    args = parser.parse_args(argv)
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    args.run.mkdir(parents=True, exist_ok=False)
    execute(args.host.resolve(), args.run.resolve(), args.repetitions,
            tuple(dict.fromkeys(args.scenarios)))


if __name__ == "__main__":
    main()
