#!/usr/bin/env python3
"""Shared path registry, environment evidence, and fail-closed smoke gate."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

import storage
import smoke_profile
from supervisor import load_json, published, write_json, atomic_write


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SCHEMA = "fs-compare-v2-smoke/2"
KNOWN_UNSUPPORTED = {
    "P012": r"EXT4-fs \(loop[0-9]+\): can't mount with journal_async_commit in data=ordered mode",
    "P085": r"mkfs\.btrfs: unrecognized option '--enable-simple-quota'",
    "P101": r"BTRFS error \(device loop[0-9]+\): cannot disable free-space-tree",
    "P133": r"cryptsetup: Option --iv-large-sectors is not allowed with luksFormat action\.",
}
NEVER_EXCLUDE = re.compile(
    r"timed? out|timeout|ENOSPC|No space left|EIO|I/O error|"
    r"Kernel panic|\bOops:|\bBUG:|Permission denied|No such file|"
    r"tool_version_error|environment_error", re.I)


def table(path):
    with Path(path).open() as stream:
        return list(csv.DictReader((line for line in stream if not line.startswith("#")),
                                   delimiter="\t"))


def registry():
    paths = table(HERE / "paths.tsv")
    configs = {row["id"]: row for row in table(HERE / "fs-compare-configs.tsv")}
    variants = {row["id"]: row for row in table(HERE / "fs-compare-phase2-variants.tsv")}
    if any(row["tests"] not in ("std", "std+T6") for row in variants.values()):
        raise ValueError("unknown variant test profile")
    return paths, configs, variants


def validate(config, test):
    paths, configs, variants = registry()
    if config not in configs and config not in variants:
        raise ValueError(f"unknown configuration: {config}")
    if test not in {row["test"] for row in paths}:
        raise ValueError(f"unknown test: {test}")


def read_plan(path):
    rows, seen = [], set()
    for line in Path(path).read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 3:
            raise ValueError("plan requires three TSV columns")
        config, test, repetition = fields
        validate(config, test)
        if not re.fullmatch(r"[1-9][0-9]*", repetition):
            raise ValueError("invalid repetition number")
        if tuple(fields) in seen:
            raise ValueError("duplicate plan row")
        seen.add(tuple(fields))
        rows.append(tuple(fields))
    if not rows:
        raise ValueError("plan contains no rows")
    return rows


def generated(profile, repetitions, legacy=False):
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    paths, configs, variants = registry()
    rows = []
    if profile in ("all", "phase1"):
        for path in sorted(paths, key=lambda row: int(row["phase1"])):
            if path["phase1"] == "0":
                continue
            order = list(configs)
            if legacy and path["test"] == "T1":
                first = [config for config in ("L3", "I1", "I2") if config in configs]
                order = first + [config for config in configs if config not in first]
            count = int(path["legacy_repetitions"]) if legacy else repetitions
            rows += [(config, path["test"], str(number)) for config in order
                     for number in range(1, count + 1)]
    if profile in ("all", "phase2"):
        for config, variant in variants.items():
            for path in sorted(paths, key=lambda row: int(row["phase2"])):
                if path["phase2"] == "0" or (path["test"] == "T6" and variant["tests"] != "std+T6"):
                    continue
                count = int(path["legacy_repetitions"]) if legacy else repetitions
                rows += [(config, path["test"], str(number)) for number in range(1, count + 1)]
    return rows


def plan_bytes(rows):
    return "".join("\t".join(row) + "\n" for row in rows).encode()


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def unique_config(output, pattern):
    matches = list((output / "build").glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected one real generated config: {pattern}; found {len(matches)}")
    return matches[0]


def require_symbols(path, symbols):
    lines = set(path.read_text().splitlines())
    missing = [symbol for symbol in symbols if f"{symbol}=y" not in lines]
    if missing:
        raise ValueError(f"required built-in config missing in {path.name}: {missing}")


def environment(output, runner=subprocess.run):
    output = Path(output).resolve()
    linux = unique_config(output, "linux*/.config")
    busybox = unique_config(output, "busybox-*/.config")
    require_symbols(linux, [line.split("=")[0] for line in
                            (HERE / "fs-compare.fragment").read_text().splitlines()
                            if line.endswith("=y")])
    require_symbols(busybox, ["CONFIG_CHATTR", "CONFIG_BB_SYSCTL"])
    require_symbols(output / ".config", [line.split("=")[0] for line in
                    (HERE / "fs-compare.buildroot.fragment").read_text().splitlines()
                    if line.endswith("=y")])
    release = linux.parent / "include/config/kernel.release"
    if not re.fullmatch(r"[A-Za-z0-9._+-]+", release.read_text().strip()):
        raise ValueError("invalid built kernel release")
    inputs = [output / ".config", linux, busybox, release]
    inputs += [output / "images" / name for name in
               ("Image", "bcm2710-rpi-3-b.dtb", "rootfs.squashfs", "sdcard.img")]
    inputs += [output / "fs-compare" / name for name in
               ("replay-log", "replay-log.provenance", "fs-compare-workload")]
    inputs += [path for path in HERE.iterdir() if path.is_file()]
    smoke_profile.load()
    inputs += [ROOT / "board/cardputerzero/qemu/run-qemu.sh"]
    for name, expected in (("KERNEL_IMAGE", inputs[4]), ("DTB_IMAGE", inputs[5])):
        if os.environ.get(name) and Path(os.environ[name]).resolve() != expected.resolve():
            raise ValueError(f"{name} override does not match the checked build")
    tools = {name: (shutil.which(name), ["--version"], {0}) for name in
             ("bash", "python3", "cp", "dd", "truncate", "stat", "sha256sum", "shuf",
              "install", "awk", "grep", "sed", "git", "flock", "mkdir", "dirname", "basename",
              "head", "tail", "cut", "tr", "date", "tee", "sleep", "cat", "mv", "rm",
              "cmp", "find", "sort", "wc", "readlink", "mktemp")}
    tools["qemu"] = (shutil.which(os.environ.get("QEMU_SYSTEM_AARCH64", "qemu-system-aarch64")),
                     ["--version"], {0})
    tools["awk"] = (shutil.which("awk"), ["-W", "version"], {0})
    if os.environ.get("QEMU_DTB_BLUETOOTH", "0") != "1":
        fdtput = output / "host/bin/fdtput"
        tools["fdtput"] = (str(fdtput) if os.access(fdtput, os.X_OK) else shutil.which("fdtput"),
                           ["--version"], {0})
    for name, relative, option, statuses in (
            ("unsquashfs", "host/bin/unsquashfs", "-version", {0, 1}),
            ("mksquashfs", "host/bin/mksquashfs", "-version", {0}),
            ("sfdisk", "host/sbin/sfdisk", "--version", {0})):
        tools[name] = (str(output / relative), [option], statuses)
    versions = {}
    for name, (executable, args, statuses) in tools.items():
        if executable is None or not os.access(executable, os.X_OK):
            raise ValueError(f"required host tool missing: {name}")
        result = runner([executable, *args], capture_output=True, text=True, timeout=15)
        version = result.stdout + result.stderr
        if result.returncode not in statuses or not version.strip():
            raise ValueError(f"host version probe failed: {name}: {version}")
        versions[name] = dict(path=str(Path(executable).resolve()), version=version,
                              sha256=digest(executable))
    return dict(schema=SCHEMA, files={str(path): digest(path) for path in inputs},
                tools=versions, kernel_release=release.read_text().strip(),
                storage=dict(log_limit=storage.log_limit(),
                             max_attempts=storage.positive(os.environ.get("FSCMP_MAX_ATTEMPTS", "1"))),
                overrides={key: value for key, value in os.environ.items()
                           if key.startswith(("QEMU_", "LD_", "LC_", "PYTHON"))
                           or key in ("PATH", "ROOT_DEVICE", "ROOT_FSTYPE", "TMPDIR", "BASH_ENV",
                                      "ENV", "BASHOPTS", "SHELLOPTS", "CDPATH", "LANG", "TZ")})


def identity(env, rows):
    return hashlib.sha256(json.dumps(dict(environment=env, plan=rows),
                                    sort_keys=True).encode()).hexdigest()


def requirements(rows):
    paths, configs, variants = registry()
    required = [(config, path) for config in configs for path in paths]
    for config, variant in variants.items():
        required += [(config, path) for path in paths
                     if path["test"] == "smoke" or (path["phase2"] != "0"
                         and (path["test"] != "T6" or variant["tests"] == "std+T6"))]
    seen = {(config, path["test"]) for config, path in required}
    for config, test, _ in rows:
        if (config, test) not in seen:
            required += [(config, path) for path in paths if path["test"] == test]
            seen.add((config, test))
    return required


def unsupported(config, records, text, child_status):
    pattern = KNOWN_UNSUPPORTED.get(config)
    if not pattern or child_status != 1 or NEVER_EXCLUDE.search(text):
        return None
    aborts = {}
    for record in records:
        if record.get("category") == "process" and record["text"].startswith("phase status: "):
            phase = json.loads(record["text"].removeprefix("phase status: "))
            if (phase.get("reaped") is True and phase.get("mode") == "abort"
                    and phase.get("error") is None and phase.get("returncode") in (0, -15)
                    and phase.get("fallback") == ["SIGTERM"]
                    and isinstance(phase.get("stop_pid"), int) and phase["stop_pid"] > 0):
                aborts[record.get("phase")] = phase
    lines = []
    for record in records:
        if record.get("expected"):
            continue
        text_line = record["text"]
        abort = aborts.get(record.get("phase"))
        if (record.get("category") == "qemu" and abort
                and re.fullmatch(r"(?:\S*/)?qemu-system-[\w-]+: terminating on signal 15 from pid "
                                 + str(abort["stop_pid"]) + r" \([^\r\n()]+\)\s*", text_line)):
            continue
        if record.get("category") == "process":
            if text_line == "driver exit status=1":
                continue
            if text_line.startswith("phase status: "):
                phase = json.loads(text_line.removeprefix("phase status: "))
                if (phase.get("reaped") is True and phase.get("mode") == "abort"
                        and phase.get("error") is None and
                        (phase.get("returncode") == 0 or record.get("phase") in aborts)):
                    continue
        lines.append(text_line)
    expected = {record["text"] for record in records if record.get("expected")}
    matches = [line for line in text.splitlines()
               if re.search(pattern, line) and line not in expected]
    if not matches:
        return None
    # The guest/driver exit caused by that rejected setup is allowed, nothing else.
    consequences = re.compile(r"msd\.fscmp: error=(?:mount_failed|guest_exit status=1|"
                              r"setup_step_failed.*)|Test did not finish")
    if any(not re.search(pattern, line) and not consequences.search(line) for line in lines):
        return None
    return matches


def run_probe(directory, config, path, env, output):
    with smoke_profile.context():
        return _run_probe(directory, config, path, env, output)


def _run_probe(directory, config, path, env, output):
    started = time.monotonic()
    storage.check_capacity()
    run_id = f"probe-{config}-{path['path']}"
    command = [str(HERE / "fs-compare.sh"), config, path["test"], run_id]
    if path["points"] == "first":
        command += ["--points", "first"]
    child_env = dict(os.environ, OUTPUT_DIR=str(output), QEMU_LOG_DIR=str(directory),
                     FSCMP_PREFLIGHT_WORKER="1", FSCMP_SMOKE="1",
                     FSCMP_EXPECT_KERNEL=env["kernel_release"])
    launcher = directory / f"{run_id}.launcher.log"
    child_env["FSCMP_LAUNCH_LOG"] = str(launcher)
    with launcher.open("x") as log:
        child = storage.run_child(command, child_env, log)
    run = directory / run_id
    archive = storage.finish(run, path["test"], child.returncode, launcher)
    result = published(run / "summary.csv")
    logs = list(run.glob("qemu-*.log")) + [run / "host.log"]
    text = "\n".join(path.read_text(errors="replace") for path in logs if path.is_file())
    records = [json.loads(line) for line in (run / "errors.jsonl").read_text().splitlines()]
    ok = child.returncode == 0 and result is not None and result.get("status") == "ok"
    phases = path["phases"].split(",")
    ok = ok and all(f"msd.fscmp: environment_ok kernel={env['kernel_release']}" in
                    (run / f"qemu-{phase}.log").read_text(errors="replace") for phase in phases)
    ok = ok and profile_evidence(path["test"], run, phases, text)
    return dict(config=config, path=path["path"], test=path["test"], phases=phases,
                elapsed_seconds=time.monotonic() - started,
                ok=ok, child_status=child.returncode, run=str(run),
                command=command, option=registry()[2].get(config), archive=archive,
                evidence={str(file): digest(file) for file in
                          [run / "result.json", run / "summary.csv", run / "errors.jsonl",
                           run / storage.STATE, *logs] if file.is_file()},
                unsupported=unsupported(config, records, text, child.returncode))


def profile_evidence(test, run, phases, text):
    profile = smoke_profile.load()
    marker = f"msd.fscmp: SMOKE_PROFILE sha256={smoke_profile.fingerprint()}"
    if not all(marker in (run / f"qemu-{phase}.log").read_text(errors="replace") for phase in phases):
        return False
    if test in {"T1", "T1-negative", "T1-final", "T1-negative-final", "T1-sample",
                "T2", "T4-sync", "T4-nosync", "T5"}:
        marker = (f"workload_profile name=smoke W1_files={profile['w1_files']} "
                  f"W2_updates={profile['w2_updates']} W3_records={profile['w3_records']} "
                  f"W3_fsync_every=50 W4_bytes={profile['w4_bytes']}")
        if marker not in text:
            return False
    if test == "T5" and f"T5_LOGICAL_BYTES={smoke_profile.logical_bytes(profile)}" not in text:
        return False
    if test == "T7" and not re.search(r"T7_FINISHED filesystem=\S+ bytes=" + str(profile["t7_bytes"]), text):
        return False
    return True


def covered(certificate, fingerprint, required):
    if certificate.get("schema") != SCHEMA or certificate.get("identity") != fingerprint:
        return False
    records = {(row["config"], row["path"]): row for row in certificate.get("probes", [])}
    if len(records) != len(certificate.get("probes", [])):
        return False
    if any(not row.get("evidence") for row in records.values()):
        return False
    excluded = set(certificate.get("excluded", []))
    for config, path in required:
        row = records.get((config, path["path"]))
        if config in excluded:
            candidates = [probe for probe in records.values() if probe["config"] == config]
            if not any(probe.get("unsupported") for probe in candidates):
                return False
            continue
        if not row or row.get("ok") is not True or row.get("phases") != path["phases"].split(","):
            return False
    try:
        for row in records.values():
            if "archive" in row:
                archive = row["archive"]
                storage.verify_archive(archive["archive"], archive["manifest_sha256"])
        return all(digest(file) == value for row in records.values()
                   for file, value in row["evidence"].items())
    except (OSError, KeyError, TypeError, ValueError, storage.tarfile.TarError):
        return False


def gate(rows, directory, output, probe=run_probe, inspect=environment, parameters=None,
         expected_environment=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    env = inspect(output)
    if expected_environment is not None and env != load_json(expected_environment):
        raise ValueError("environment differs from the approved manifest")
    write_json(directory / "environment.json", env)
    if probe is run_probe:
        write_plan = directory / "requested-plan.tsv"
        atomic_write(write_plan, plan_bytes(rows))
        os.environ["FSCMP_ENVIRONMENT_FILE"] = str(directory / "environment.json")
        os.environ["FSCMP_PLAN_FILE"] = str(write_plan)
    identity_parameters = ({key: value for key, value in parameters.items() if key != "smoke_only"}
                           if parameters is not None else None)
    fingerprint = identity(env, dict(rows=rows, parameters=identity_parameters))
    required = requirements(rows)
    certificate_path = directory / "smoke-coverage.json"
    try:
        certificate = load_json(certificate_path)
        reuse = covered(certificate, fingerprint, required)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        certificate = {}
        reuse = False
    if probe is run_probe:
        maximum = storage.positive(os.environ.get("FSCMP_MAX_ATTEMPTS", "1"))
        smoke_count = 0 if reuse else len(required)
        main_count = (storage.remaining_attempts(rows, os.environ["FSCMP_MATRIX_DIR"], maximum)
                      if os.environ.get("FSCMP_MATRIX_DIR") else len(rows) * maximum)
        if parameters and parameters.get("smoke_only"):
            main_count = 0
        storage.prepare(directory, output, smoke_count + main_count,
                        counts=dict(planned_rows=len(rows), max_attempts=maximum,
                                    smoke_probes=smoke_count, remaining_main_attempts=main_count))
    if not reuse:
        attempt = directory / f"attempt-{time.time_ns()}"
        attempt.mkdir()
        write_json(attempt / "environment.json", env)
        previous = certificate
        if previous:
            write_json(attempt / "previous-coverage.json", previous)
        certificate = dict(schema=SCHEMA, identity=fingerprint, probes=[], excluded=[])
        if previous.get("schema") == SCHEMA and previous.get("identity") == fingerprint:
            for config, path in required:
                matches = [row for row in previous.get("probes", [])
                           if (row["config"], row["path"]) == (config, path["path"])]
                if len(matches) != 1:
                    continue
                row = matches[0]
                candidate = dict(schema=SCHEMA, identity=fingerprint, probes=[row],
                                 excluded=[config] if row.get("unsupported") else [])
                if covered(candidate, fingerprint, [(config, path)]):
                    certificate["probes"].append(row)
                    if row.get("unsupported") and config not in certificate["excluded"]:
                        certificate["excluded"].append(config)
        reused = {(row["config"], row["path"]) for row in certificate["probes"]}
        for config, path in required:
            if config in certificate["excluded"] or (config, path["path"]) in reused:
                continue
            result = probe(attempt, config, path, env, output)
            certificate["probes"].append(result)
            if result["unsupported"]:
                certificate["excluded"].append(config)
            write_json(certificate_path, certificate)
            print(f"smoke {len(certificate['probes'])}/{len(required)} {config}/{path['path']} "
                  f"ok={result['ok']} excluded={bool(result['unsupported'])} "
                  f"seconds={result.get('elapsed_seconds', 0):.3f}", flush=True)
            if not result["ok"] and not result["unsupported"]:
                raise ValueError(f"smoke failed: {config}/{path['path']}; main run not started")
        if not covered(certificate, fingerprint, required):
            raise ValueError("uncovered path or planned combination")
    excluded = [row for row in certificate["probes"] if row.get("unsupported")]
    write_json(directory / "excluded-options.json",
               dict(identity=fingerprint, environment=env, reason="exact-known-unsupported",
                    options=excluded))
    effective = [row for row in rows if row[0] not in certificate["excluded"]]
    atomic_write(directory / "effective-plan.tsv", plan_bytes(effective))
    if not effective:
        raise ValueError("nothing to run: all planned options excluded")
    return effective, env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    check = sub.add_parser("validate")
    check.add_argument("config")
    check.add_argument("test")
    validate_plan = sub.add_parser("validate-plan")
    validate_plan.add_argument("plan", type=Path)
    generate = sub.add_parser("generate")
    generate.add_argument("--profile", choices=["all", "phase1", "phase2"], default="all")
    generate.add_argument("--repetitions", type=int, default=3)
    generate.add_argument("--legacy", action="store_true")
    prepare = sub.add_parser("gate")
    prepare.add_argument("plan", type=Path)
    prepare.add_argument("directory", type=Path)
    prepare.add_argument("--expect-environment", type=Path)
    prepare.add_argument("--smoke-only", action="store_true")
    diagnose = sub.add_parser("diagnose")
    diagnose.add_argument("config")
    diagnose.add_argument("path")
    diagnose.add_argument("directory", type=Path)
    single = sub.add_parser("single")
    single.add_argument("config")
    single.add_argument("test")
    single.add_argument("run_id")
    single.add_argument("--points")
    single.add_argument("--expect-environment", type=Path)
    args = parser.parse_args()
    if args.action in ("gate", "single", "diagnose") and os.environ.get("FSCMP_SMOKE") is not None:
        raise ValueError("FSCMP_SMOKE is internal; use gate --smoke-only or diagnose")
    if args.action == "validate":
        validate(args.config, args.test)
    elif args.action == "validate-plan":
        read_plan(args.plan)
    elif args.action == "generate":
        sys.stdout.buffer.write(plan_bytes(generated(args.profile, args.repetitions, args.legacy)))
    else:
        output = Path(os.environ.get("OUTPUT_DIR", ROOT / "output-fscmp-v2")).resolve()
        if args.action == "gate":
            gate(read_plan(args.plan), args.directory, output,
                 parameters={"plan_sha256": digest(args.plan), "smoke_only": args.smoke_only},
                 expected_environment=args.expect_environment)
        elif args.action == "diagnose":
            paths, configs, variants = registry()
            if args.config not in {*configs, *variants}:
                raise ValueError("unknown diagnostic config")
            path = next((row for row in paths if row["path"] == args.path), None)
            if path is None:
                raise ValueError("unknown diagnostic path")
            args.directory = storage.persistent(args.directory)
            args.directory.mkdir(parents=True, exist_ok=False)
            env = environment(output)
            write_json(args.directory / "environment.json", env)
            plan = args.directory / "requested-plan.tsv"
            atomic_write(plan, plan_bytes([(args.config, path["test"], "1")]))
            os.environ["FSCMP_ENVIRONMENT_FILE"] = str(args.directory / "environment.json")
            os.environ["FSCMP_PLAN_FILE"] = str(plan)
            storage.prepare(args.directory, output, 1, counts=dict(smoke_probes=1))
            result = run_probe(args.directory, args.config, path, env, output)
            write_json(args.directory / "diagnostic.json", result)
            if not result["ok"] and not result["unsupported"]:
                raise ValueError("diagnostic failed; no coverage certificate issued")
        else:
            validate(args.config, args.test)
            root = Path(os.environ.get("QEMU_LOG_DIR", ""))
            if not root.is_absolute() or not re.fullmatch(r"[A-Za-z0-9._-]+", args.run_id):
                raise ValueError("absolute QEMU_LOG_DIR and valid run ID required")
            if (root / args.run_id).exists() or (root / f"{args.run_id}.launcher.log").exists():
                raise ValueError("refusing to overwrite an existing attempt")
            if args.points and (args.test != "T1-sample" or
                                not re.fullmatch(r"[0-9]+(?:,[0-9]+)*", args.points)):
                raise ValueError("invalid T1 points")
            rows = [(args.config, args.test, "1")]
            _, env = gate(rows, root / ".preflight", output, parameters={"points": args.points},
                          expected_environment=args.expect_environment)
            command = [str(HERE / "fs-compare.sh"), args.config, args.test, args.run_id]
            if args.points:
                command += ["--points", args.points]
            storage.check_capacity()
            launcher = root / f"{args.run_id}.launcher.log"
            child_env = dict(os.environ, FSCMP_PREFLIGHT_WORKER="1",
                             FSCMP_EXPECT_KERNEL=env["kernel_release"], FSCMP_LAUNCH_LOG=str(launcher))
            with launcher.open("x") as log:
                child = storage.run_child(command, child_env, log)
            storage.finish(root / args.run_id, args.test, child.returncode, launcher)
            return child.returncode or int(published(root / args.run_id / "summary.csv")["status"] != "ok")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"fs-compare-preflight: {error}", file=sys.stderr)
        sys.exit(1)
