#!/usr/bin/env python3
"""Keep excluded attempts separate from the final five-repeat comparison."""

import argparse
import csv
import json
from pathlib import Path
import re
import statistics

from build import ROOT, VARIANTS, needed, sha
from runtime import parse_config, parse_serial


def putty_protocol_ids(data):
    patterns = dict(kex=rb"(?:diffie-hellman-|ecdh-sha2-|curve25519-|sntrup[0-9]|mlkem[0-9])[\w@+.-]+",
                    cipher=rb"(?:aes(?:128|192|256)-(?:cbc|ctr|gcm)(?:@openssh.com)?|chacha20-poly1305@openssh.com|3des-(?:cbc|ctr)|blowfish-(?:cbc|ctr)|arcfour(?:128|256)?|des-cbc@ssh.com)",
                    mac=rb"hmac-[\w@+.-]+",
                    hostkey=rb"(?:ssh-(?:ed25519|rsa|dss)|rsa-sha2-(?:256|512)|ecdsa-sha2-nistp(?:256|384|521))(?:-cert-v01@openssh.com)?")
    return {kind: sorted({match.group()[:-1].decode() for match in re.finditer(pattern + rb"\x00", data)})
            for kind, pattern in patterns.items()}


def process_accepted(process):
    return (process.get("qmp_quit") is True and process.get("returncode") == 0
            and process.get("fallback") == [] and process.get("error") is None)


def load_process(directory):
    path = directory / "process.json"
    if path.exists():
        return json.loads(path.read_text())
    failure = directory / "failure.json"
    if failure.exists():
        return dict(error="process.json missing", failure=json.loads(failure.read_text()))
    raise ValueError(f"missing process/failure evidence: {directory}")


def summarize(build, measure, attempts, final):
    final_process = load_process(final)
    if final not in attempts or not process_accepted(final_process):
        raise ValueError("final runtime process was not accepted")
    rows = []
    for directory in [build, measure, *attempts]:
        path = directory / "results.csv"
        if path.exists():
            with path.open(newline="") as stream:
                records = list(csv.DictReader(stream))
            for row in records:
                row["run_id"] = directory.name + "/" + row["run_id"]
                if directory == build and row["metric"] in ("installed_added", "squashfs"):
                    row["valid"] = "0"
                    row["note"] += "; sort-wrapper trial excluded from final size comparison"
                if directory in attempts and directory != final:
                    row["valid"] = "0"
                    row["note"] += "; preflight or rejected attempt, not final aggregation"
                rows.append(row)
        if directory in attempts:
            process = load_process(directory)
            accepted = directory == final and process_accepted(process)
            rows.append(dict(run_id=directory.name + "/attempt", variant="all", repeat=1,
                             metric="attempt_accepted", value=int(accepted), unit="bool", valid=int(accepted),
                             note=json.dumps(process, ensure_ascii=False)))
    if len({row["run_id"] + "/" + row["metric"] for row in rows}) != len(rows):
        raise ValueError("duplicate run/metric")
    with (measure / "results.csv").open(newline="") as stream:
        measurements = list(csv.DictReader(stream))
    sizes = {}
    for variant in ("baseline", *VARIANTS):
        subset = [row for row in measurements if row["variant"] == variant and row["metric"] == "squashfs"]
        if {int(row["repeat"]) for row in subset} != set(range(1, 6)) or len(subset) != 5:
            raise ValueError("incomplete size repeats")
        values = [int(row["value"]) for row in subset]
        if len({row["note"] for row in subset}) != 1:
            raise ValueError("A/A hash mismatch")
        sizes[variant] = dict(median=statistics.median(values), minimum=min(values), maximum=max(values),
                              image_sha256=subset[0]["note"].split("=", 1)[1])
    serial = (final / "serial.log").read_text(errors="replace").replace("\r", "")
    trials = parse_serial(serial, VARIANTS, 5)
    if len(trials) != 30:
        raise ValueError("incomplete final runtime")
    report = dict(sizes=sizes, candidates={}, algorithms={}, putty_binary_protocol_ids={},
                  final_process=final_process)
    for variant in VARIANTS:
        files = json.loads((build / variant / "files.json").read_text())
        binary = build / variant / "root" / files[0]["path"]
        report["candidates"][variant] = dict(files=files, direct_needed=needed(binary),
            dependency_closure=json.loads((build / variant / "dependencies.json").read_text()),
            installed_added=sum(row["bytes"] for row in files),
            squashfs_delta=sizes[variant]["median"] - sizes["baseline"]["median"],
            good=[code for (name, condition, _), code in trials.items() if name == variant and condition == "good"],
            wrong=[code for (name, condition, _), code in trials.items() if name == variant and condition == "wrong"])
    for variant, kind, body in re.findall(r"SSH_ALGORITHMS (\S+) (\S+)\n(.*?)SSH_ALGORITHMS_END", serial, re.S):
        report["algorithms"].setdefault(variant, {})[kind] = body.strip().splitlines()
    binary = build / "putty/root/usr/bin/plink"
    report["putty_binary_protocol_ids"] = putty_protocol_ids(binary.read_bytes())
    report["putty_binary_protocol_ids"]["limitation"] = "ELF文字列とsource登録表の照合候補。runtime queryではなく全algorithmの交渉試験でもない"
    report["home_changes"] = {}
    report["writable_opens"] = {}
    report["trace_available"] = {}
    for variant in VARIANTS:
        homes, operations = [], []
        traced = 0
        for condition in ("good", "wrong"):
            for repeat in range(1, 6):
                body = serial.split(f"SSH_BEGIN {variant} {condition} {repeat}", 1)[1].split(
                    f"SSH_RESULT {variant} {condition} {repeat}", 1)[0]
                before = body.split("SSH_HOME_BEFORE", 1)[1].split("SSH_HOME_AFTER", 1)[0]
                after = body.split("SSH_HOME_AFTER", 1)[1].split("SSH_TRACE_BEGIN", 1)[0]
                parse = lambda text: {name: digest for digest, name in re.findall(r"(?m)^([a-f0-9]{64})  (.+)$", text)}
                first, second = parse(before), parse(after)
                homes.append(dict(condition=condition, repeat=repeat,
                                  changed=sorted(path for path in first.keys() | second.keys() if first.get(path) != second.get(path))))
                has_begin, has_end = "SSH_TRACE_BEGIN" in body, "SSH_TRACE_END" in body
                if has_begin != has_end:
                    raise ValueError("incomplete trace block")
                if has_begin:
                    traced += 1
                    trace = body.split("SSH_TRACE_BEGIN", 1)[1].split("SSH_TRACE_END", 1)[0]
                    operations.extend(re.sub(r"^\d+\s+", "", line) for line in trace.splitlines()
                                      if any(token in line for token in ("O_WRONLY", "O_RDWR", "mkdir(", "rename(", "unlink(")))
        report["home_changes"][variant] = homes
        report["writable_opens"][variant] = sorted(set(operations)) if traced == 10 else None
        report["trace_available"][variant] = dict(observed=traced, expected=10)
    block = serial.split("SSH_CONFIG_BEGIN", 1)[1].split("SSH_CONFIG_END", 1)[0]
    report["openssh_effective_config"] = parse_config(block)
    report["final_inputs"] = json.loads((final / "inputs.json").read_text())
    report["run_qemu_hash_lines"] = [line.replace(str(ROOT), ".") for line in serial.splitlines() if "run-qemu: sha256" in line]
    return rows, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--measure", type=Path, required=True)
    parser.add_argument("--attempts", type=Path, nargs="+", required=True)
    parser.add_argument("--final", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows, report = summarize(args.build, args.measure, args.attempts, args.final)
    args.out.mkdir(parents=True, exist_ok=False)
    with (args.out / "results.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["run_id", "variant", "repeat", "metric", "value", "unit", "valid", "note"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    text = json.dumps(report, ensure_ascii=False, indent=2).replace(str(ROOT), ".")
    (args.out / "summary.json").write_text(text + "\n")
    print(f"ok - {len(rows)} raw rows; 20 A/A size images; final runtime 30/30 expected outcomes")


if __name__ == "__main__":
    main()
