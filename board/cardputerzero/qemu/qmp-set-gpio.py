#!/usr/bin/env python3
import json
import socket
import sys
import time


def receive(stream):
    line = stream.readline()
    if not line:
        raise RuntimeError("QMP closed the connection")
    return json.loads(line)


def command(stream, command_id, name, arguments=None):
    message = {"execute": name, "id": command_id}
    if arguments is not None:
        message["arguments"] = arguments
    stream.write((json.dumps(message) + "\r\n").encode())
    while True:
        reply = receive(stream)
        if reply.get("id") != command_id:
            continue
        if "error" in reply:
            raise RuntimeError(f"QMP {name} failed: {reply['error']}")
        return reply


def main():
    if len(sys.argv) != 5:
        raise SystemExit(
            f"Usage: {sys.argv[0]} <socket> <object> <property> <true|false>"
        )

    socket_path, object_path, property_name, value_text = sys.argv[1:]
    if value_text not in ("true", "false"):
        raise SystemExit("GPIO value must be true or false")

    deadline = time.monotonic() + 15
    while True:
        try:
            connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            connection.connect(socket_path)
            break
        except OSError:
            connection.close()
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.05)

    with connection:
        stream = connection.makefile("rwb", buffering=0)
        greeting = receive(stream)
        if "QMP" not in greeting:
            raise RuntimeError(f"Unexpected QMP greeting: {greeting}")
        command(stream, 1, "qmp_capabilities")
        request_ns = time.monotonic_ns()
        command(
            stream,
            2,
            "qom-set",
            {
                "path": object_path,
                "property": property_name,
                "value": value_text == "true",
            },
        )
        response_ns = time.monotonic_ns()
        print(json.dumps({"request_ns": request_ns, "response_ns": response_ns}))


if __name__ == "__main__":
    main()
