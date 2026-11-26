#!/usr/bin/env python3
"""Supervise one QEMU phase and publish fail-closed run results."""

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import tempfile
import time


SCHEMA = "fs-compare-v2/1"
MARKERS = {"run": "msd.fscmp: finished", "verify": "msd.fscmp: recovery_finished"}
CUT_MARKERS = {"T2": "msd.fscmp: workload-start", "T3": "msd.fscmp: writer-start"}
GROW_COMPLETE_MARKERS = ("msd-data: setup synchronized",
                         "msd-data: setup synchronized / 初期設定の同期が完了しました。")


def atomic_write(path, content):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_json(path, value):
    atomic_write(path, (json.dumps(value, indent=2) + "\n").encode())


def load_json(path):
    with Path(path).open() as stream:
        return json.load(stream)


def qmp_quit(path, timeout):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect(str(path))
        with connection.makefile("rwb") as stream:
            if "QMP" not in json.loads(stream.readline()):
                raise ValueError("QMP greeting missing")
            for command in ("qmp_capabilities", "quit"):
                stream.write(json.dumps({"execute": command, "id": command}).encode() + b"\n")
                stream.flush()
                deadline = time.monotonic() + timeout
                while True:
                    connection.settimeout(max(0.001, deadline - time.monotonic()))
                    response = json.loads(stream.readline())
                    if response.get("id") == command:
                        if "return" not in response:
                            raise ValueError(f"QMP {command} rejected: {response}")
                        break
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"QMP {command} timed out")


def signal_group(process, number):
    try:
        os.killpg(process.pid, number)
        return True
    except ProcessLookupError:
        return False


def reap(process, timeout):
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def supervise(directory, phase, test, command, timeout=86400, grace=5):
    directory = Path(directory)
    result_path = directory / f"phase-{phase}.json"
    request_path = directory / f"request-{phase}.json"
    log_path = directory / f"qemu-{phase}.log"
    if result_path.exists() or request_path.exists() or log_path.exists():
        raise FileExistsError("phase output already exists")
    result = dict(schema=SCHEMA, phase=phase, test=test, reaped=False,
                  returncode=None, mode=None, qmp_quit=False, fallback=[],
                  cut_intent=False, cut_sent=False, error=None)
    process = None
    interrupted = False

    def interrupt(_number, _frame):
        nonlocal interrupted
        interrupted = True

    handlers = {number: signal.signal(number, interrupt)
                for number in (signal.SIGTERM, signal.SIGINT)}
    try:
        with tempfile.TemporaryDirectory(prefix="fscmp-v2-") as temporary, log_path.open("xb") as log:
            qmp_path = Path(temporary) / "qmp.sock"
            environment = dict(os.environ, QEMU_QMP_SOCKET=str(qmp_path))
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       env=environment, start_new_session=True)
            result["pid"] = process.pid
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if interrupted or time.monotonic() >= deadline:
                    result["mode"] = "abort"
                    result["error"] = "interrupted" if interrupted else "timeout"
                    break
                if request_path.exists():
                    result["mode"] = load_json(request_path)["mode"]
                    break
                time.sleep(0.02)
            if process.poll() is None:
                if result["mode"] == "normal":
                    qmp_quit(qmp_path, grace)
                    result["qmp_quit"] = True
                    reap(process, grace)
                elif result["mode"] == "cut":
                    text = log_path.read_text(errors="replace")
                    if phase != "run" or test not in CUT_MARKERS or CUT_MARKERS[test] not in text:
                        raise ValueError("unplanned cut or missing cut marker")
                    write_json(directory / "cut-intent.json", {
                        "schema": SCHEMA, "test": test, "phase": phase,
                        "marker": CUT_MARKERS[test], "monotonic": time.monotonic(),
                    })
                    result["cut_intent"] = True
                    result["cut_sent"] = signal_group(process, signal.SIGKILL)
                    reap(process, grace)
                elif result["mode"] == "abort":
                    result["stop_pid"] = os.getpid()
                else:
                    raise ValueError("unknown stop request")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result["error"] = str(error)
    finally:
        if process is not None:
            for number in (signal.SIGTERM, signal.SIGKILL):
                if process.poll() is None:
                    result["fallback"].append(signal.Signals(number).name)
                    signal_group(process, number)
                    reap(process, grace)
            result["returncode"] = process.poll()
            result["reaped"] = result["returncode"] is not None
        for number, handler in handlers.items():
            signal.signal(number, handler)
        result["log_sha256"] = hashlib.sha256(log_path.read_bytes()).hexdigest()
        result["marker"] = MARKERS[phase] in log_path.read_text(errors="replace")
        write_json(result_path, result)
    return result


def phase_ok(result, test, phase):
    if not isinstance(result, dict) or result.get("schema") != SCHEMA:
        return False
    if result.get("phase") != phase or result.get("test") != test:
        return False
    if result.get("reaped") is not True or result.get("error") is not None or result.get("fallback") != []:
        return False
    if phase == "run" and test in CUT_MARKERS:
        return (result.get("mode") == "cut" and result.get("cut_intent") is True
                and result.get("cut_sent") is True and result.get("returncode") == -signal.SIGKILL)
    return (result.get("mode") == "normal" and result.get("qmp_quit") is True
            and result.get("returncode") == 0 and result.get("marker") is True)


def boot_serial_lines(lines, enabled):
    pending = ""
    origin = 0
    for number, text in enumerate(lines, 1):
        marker = text.startswith(("msd.fscmp: expected_errors_begin kind=",
                                  "msd.fscmp: expected_errors_end kind=")) or (
                                      enabled() and text.startswith("msd.fscmp:"))
        if not enabled() or text.startswith("msd.fscmp:"):
            if pending:
                yield origin, pending
                pending = ""
            if not marker:
                yield number, text
                continue
        stamps = list(re.finditer(r"\[\s*[0-9]+\.[0-9]+\] ", text))
        if stamps:
            prefix = text[:stamps[0].start()]
            if prefix:
                if marker:
                    yield number, prefix
                else:
                    if not pending:
                        origin = number
                    pending += prefix
            for index, stamp in enumerate(stamps):
                end = stamps[index + 1].start() if index + 1 < len(stamps) else len(text)
                yield number, text[stamp.start():end]
        elif pending:
            yield origin, pending + text
            pending = ""
        else:
            yield number, text
    if pending:
        yield origin, pending


def aggregate_errors(logs, test):
    records = []
    boot_rules = load_json(Path(__file__).with_name("boot-diagnostics.json"))
    wifi = next(entry for entry in boot_rules["entries"] if entry["id"] == "wifi-sdio")
    wifi_seen = set()
    for phase, path in logs:
        context = None
        lines = Path(path).read_text(errors="replace").splitlines()
        qemu = machine = kernel = model = closed = False
        grow_pending = False
        grow_complete = any(marker in lines for marker in GROW_COMPLETE_MARKERS)
        smoke = any(re.fullmatch(r"msd\.fscmp: SMOKE_PROFILE sha256=[a-f0-9]{64}", text)
                    for _, text in boot_serial_lines(lines, lambda: True))
        def known_environment():
            return (smoke and phase in ("run", "verify") and Path(path).name == f"qemu-{phase}.log"
                    and qemu and machine and kernel and model)

        for line_number, text in boot_serial_lines(lines, known_environment):
            normalized = re.sub(r"^\[\s*[0-9]+\.[0-9]+\] ", "", text)
            qemu |= text == "run-qemu: version=" + boot_rules["qemu"]
            machine |= text == boot_rules["machine"]
            kernel |= normalized.startswith("Linux version " + boot_rules["kernel"] + " ")
            model |= normalized == "Machine model: Raspberry Pi 3 Model B"
            closed |= text.startswith("msd.fscmp:")
            boot = known_environment() and not closed
            benign = None
            if (known_environment() and phase in wifi["phases"]
                    and re.fullmatch(wifi["pattern"], normalized)):
                if phase not in wifi_seen:
                    benign = wifi
                wifi_seen.add(phase)
            if boot:
                for entry in boot_rules["entries"]:
                    if (entry["id"] != "wifi-sdio" and phase in entry["phases"]
                            and re.fullmatch(entry["pattern"], normalized)
                            and (entry["id"] != "grow-reread-busy" or (grow_pending and grow_complete))):
                        benign = entry
                        break
            if re.fullmatch(r"msd-data-grow: extending partition [47] to the end of /dev/mmcblk0", text):
                grow_pending = True
            elif not re.match(r"^\[\s*[0-9]+\.[0-9]+\] ", text):
                grow_pending = False
            if re.search(r"msd\.fscmp: environment_dm_target=[\w-]+\s+v[0-9.]+\s*$", text):
                continue
            begin = re.search(r"msd\.fscmp: expected_errors_begin kind=(\S+)", text)
            end = re.search(r"msd\.fscmp: expected_errors_end kind=(\S+)", text)
            if begin or end:
                kind = (begin or end)[1]
                allowed = phase == "run" and ((test.startswith("T1") and kind == "T1_replay")
                                              or (test == "T6" and kind == "T6_corruption"))
                valid = allowed and ((begin and context is None) or (end and context == kind))
                if not valid:
                    records.append(dict(file=Path(path).name, line=line_number, phase=phase,
                                        category="context", expected=False, text=text))
                context = kind if begin and valid else None
                continue
            category = None
            if re.search(r"msd\.fscmp: error=|tool_version_error", text):
                category = "guest"
            elif re.search(r"Kernel panic|\bOops:|\bBUG:|\b(?:EIO|ENOSPC)\b|No space left|I/O error.*dev (?:mmcblk|sd[a-z]|nvme)", text):
                category = "kernel-fatal"
            elif re.search(r"^(?:\S*/)?qemu(?:-system-[\w-]+)?: (?!warning:)", text, re.I):
                category = "qemu"
            elif re.search(r"\b(error|failed|failure|fatal)\b|not found|No such file|Permission denied|No space left|Refusing |Could not |Timed out |did not finish|T1_(?:MANIFEST_FAIL|MOUNT_ERR|FSCK_ERR)|T6_READCHECK exit=[234]", text, re.I):
                category = "diagnostic"
            if category:
                t7_btrfs_ok = (test == "T7" and phase == "run" and re.fullmatch(
                    r"msd\.fscmp: T7_STEP command=btrfs found [0-9]+ bytes used, no error found", text))
                expected = bool(category == "diagnostic" and (benign or t7_btrfs_ok or (context and (
                    re.search(r"T1_(?:MANIFEST_FAIL|MOUNT_ERR|FSCK_ERR)", text)
                    or re.search(r"EXT4-fs error|F2FS-fs.*error|BTRFS (?:error|warning)|checksum error|csum failed|device-mapper: integrity:", text, re.I)
                    or re.search(r"I/O error.*dev (?:dm-\d+|loop\d+)", text)
                    or re.search(r"T6_READCHECK exit=[23](?:\s|$)", text)))))
                records.append(dict(file=Path(path).name, line=line_number, phase=phase,
                                    category=category, expected=expected, text=text,
                                    **({"known_boot": benign["id"], "reason": benign["reason"],
                                        "source": benign["source"]} if expected and benign else {})))
        if context is not None:
            records.append(dict(file=Path(path).name, line=0, phase=phase, category="context",
                                expected=False, text="expected error context not closed"))
    return records


def finalize(directory, test, driver_status, rescan=False):
    directory = Path(directory)
    if (directory / "result.json").exists() and not rescan:
        raise FileExistsError("final result already exists")
    if rescan and (directory / "result.json").exists() and not (directory / "result-before-archive.json").exists():
        atomic_write(directory / "result-before-archive.json", (directory / "result.json").read_bytes())
    logs = [("host", path) for path in [directory / "host.log", directory / "launcher.log"] if path.exists()]
    logs += [(phase, directory / f"qemu-{phase}.log") for phase in ("run", "verify")
             if (directory / f"qemu-{phase}.log").exists()]
    logs += [("host", path) for path in sorted(directory.glob("supervisor-*.log"))]
    errors = aggregate_errors(logs, test)
    if (directory / "log-limit.json").exists():
        errors.append(dict(file="log-limit.json", line=0, phase="host", category="capacity",
                           expected=False, text="log size cap exceeded; raw logs preserved"))
    phases = {}
    valid = driver_status == 0
    if not valid:
        errors.append(dict(file="host.log", line=0, phase="host", category="process",
                           expected=False, text=f"driver exit status={driver_status}"))
    for phase in (["run", "verify"] if test in CUT_MARKERS else ["run"]):
        try:
            result = load_json(directory / f"phase-{phase}.json")
            log = directory / f"qemu-{phase}.log"
            accepted = phase_ok(result, test, phase)
            accepted = hashlib.sha256(log.read_bytes()).hexdigest() == result["log_sha256"] and accepted
            marker = CUT_MARKERS[test] if test in CUT_MARKERS and phase == "run" else MARKERS[phase]
            accepted = marker in log.read_text(errors="replace") and accepted
            if test in CUT_MARKERS and phase == "run":
                intent = load_json(directory / "cut-intent.json")
                accepted = (intent.get("test") == test and intent.get("phase") == "run"
                            and intent.get("marker") == CUT_MARKERS[test]) and accepted
            valid = accepted and valid
            if not accepted or result.get("mode") == "cut":
                errors.append(dict(file=f"phase-{phase}.json", line=0, phase=phase,
                                   category="process", expected=accepted,
                                   text=f"phase status: {json.dumps(result, sort_keys=True)}"))
            phases[phase] = result
        except (OSError, ValueError, KeyError, TypeError):
            valid = False
            phases[phase] = None
            errors.append(dict(file=f"phase-{phase}.json", line=0, phase=phase,
                               category="process", expected=False, text="missing or invalid phase evidence"))
    valid = valid and not any(not error["expected"] for error in errors)
    row = None
    fieldnames = []
    try:
        with (directory / "summary.pending.csv").open(newline="") as stream:
            reader = csv.DictReader(stream)
            fieldnames = reader.fieldnames
            rows = list(reader)
        if len(rows) != 1 or rows[0].get("run_id") != directory.name or rows[0].get("test") != test:
            raise ValueError("invalid pending summary")
        row = rows[0]
        valid = valid and row.get("status") == "ok"
    except (OSError, ValueError, TypeError, csv.Error):
        valid = False
    atomic_write(directory / "errors.jsonl", "".join(json.dumps(error) + "\n" for error in errors).encode())
    atomic_write(directory / "errors.txt", "".join(
        f'{error["file"]}:{error["line"]} [{error["phase"]}/{error["category"]}/'
        f'{"expected" if error["expected"] else "fatal"}] {error["text"]}\n' for error in errors).encode())
    status = "ok" if valid else "fail:final_judge"
    summary_hash = None
    if row is not None:
        row["status"] = status
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)
        content = buffer.getvalue().encode()
        atomic_write(directory / "summary.csv", content)
        summary_hash = hashlib.sha256(content).hexdigest()
    result = dict(schema=SCHEMA, run_id=directory.name, test=test, status=status,
                  driver_status=driver_status, phases=phases, summary_sha256=summary_hash,
                  fatal_errors=sum(not error["expected"] for error in errors))
    write_json(directory / "result.json", result)
    return result


def published(summary):
    try:
        storage = Path(summary).parent / ".storage.json"
        if storage.exists():
            state = load_json(storage)
            if state.get("complete") is not True or state.get("cleaned") is not True:
                return None
        result = load_json(Path(summary).parent / "result.json")
        with Path(summary).open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        if (len(rows) == 1 and result.get("schema") == SCHEMA
                and result.get("run_id") == rows[0].get("run_id") == Path(summary).parent.name
                and result.get("test") == rows[0].get("test")
                and result.get("status") == rows[0].get("status")
                and result.get("summary_sha256") == hashlib.sha256(Path(summary).read_bytes()).hexdigest()):
            return result
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def matrix_ok(summary, child_status):
    result = published(summary)
    if child_status != 0 or result is None or result.get("status") != "ok":
        return False
    child = Path(summary).parent / "matrix-child.json"
    try:
        if load_json(child).get("status") != 0:
            return False
    except (OSError, ValueError, AttributeError):
        return False
    test = result["test"]
    phases = result.get("phases")
    return (result.get("driver_status") == 0 and result.get("fatal_errors") == 0
            and isinstance(phases, dict) and all(phase_ok(phases.get(phase), test, phase)
                for phase in (["run", "verify"] if test in CUT_MARKERS else ["run"])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    run = commands.add_parser("run")
    run.add_argument("directory", type=Path)
    run.add_argument("phase", choices=MARKERS)
    run.add_argument("test")
    run.add_argument("--grace", type=float, default=5)
    run.add_argument("--timeout", type=float, default=86400)
    run.add_argument("command", nargs=argparse.REMAINDER)
    request = commands.add_parser("request")
    request.add_argument("directory", type=Path)
    request.add_argument("phase", choices=MARKERS)
    request.add_argument("mode", choices=("normal", "cut", "abort"))
    final = commands.add_parser("finalize")
    final.add_argument("directory", type=Path)
    final.add_argument("test")
    final.add_argument("status", type=int)
    matrix = commands.add_parser("matrix")
    matrix.add_argument("summary", type=Path)
    matrix.add_argument("status", type=int)
    publish = commands.add_parser("published")
    publish.add_argument("summary", type=Path)
    child = commands.add_parser("record-child")
    child.add_argument("directory", type=Path)
    child.add_argument("status", type=int)
    args = parser.parse_args()
    if args.operation == "run":
        if not args.command or args.grace <= 0 or args.timeout <= 0:
            parser.error("launcher command and positive timeouts required")
        result = supervise(args.directory, args.phase, args.test, args.command, args.timeout, args.grace)
        return int(not phase_ok(result, args.test, args.phase))
    if args.operation == "request":
        write_json(args.directory / f"request-{args.phase}.json", {"mode": args.mode})
        return 0
    if args.operation == "finalize":
        return int(finalize(args.directory, args.test, args.status)["status"] != "ok")
    if args.operation == "published":
        result = published(args.summary)
        return int(result is None or (result.get("status") == "ok" and not matrix_ok(args.summary, 0)))
    if args.operation == "record-child":
        write_json(args.directory / "matrix-child.json", {"status": args.status})
        return 0
    return int(not matrix_ok(args.summary, args.status))


if __name__ == "__main__":
    raise SystemExit(main())
