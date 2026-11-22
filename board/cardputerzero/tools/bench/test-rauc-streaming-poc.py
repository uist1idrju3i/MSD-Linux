#!/usr/bin/env python3
"""Check the fault server and signed-URL redaction without building RAUC."""

from contextlib import redirect_stderr
import http.client
import importlib.util
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


POC = module("poc", "rauc-streaming-poc.py")
GITHUB = module("observe", "rauc-github-observe.py")


class ServerTest(unittest.TestCase):
    def request(self, scenario, range_header):
        with POC.FaultServer(b"0123456789abcdef", scenario) as server:
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
            try:
                headers = {"Range": range_header} if range_header else {}
                connection.request("GET", "/download", headers=headers)
                response = connection.getresponse()
                body = response.read()
                status = response.status
            finally:
                connection.close()
                server.shutdown()
                thread.join()
        return status, body, server.events

    def test_range_and_instrumented_bytes(self):
        status, body, events = self.request("range", "bytes=4-7")
        self.assertEqual((status, body), (206, b"4567"))
        self.assertEqual(events[0]["body_bytes"], 4)

    def test_ignored_range_really_sends_full_body(self):
        status, body, events = self.request("ignore-range", "bytes=0-3")
        self.assertEqual((status, body), (200, b"0123456789abcdef"))
        self.assertEqual(events[0]["body_bytes"], 16)

    def test_empty_range_is_an_error(self):
        status, body, events = self.request("range", None)
        self.assertEqual(status, 416)
        self.assertEqual(events[0]["body_bytes"], len(body))

    def test_redaction_preserves_expiry_but_not_credentials(self):
        result = GITHUB.redact("https://example.test/object?se=2026-11-23&sig=secret&jwt=token")
        self.assertIn("se=2026-11-23", result)
        self.assertNotIn("secret", result)
        self.assertNotIn("token", result)


class CliTest(unittest.TestCase):
    def test_selected_scenarios_and_repetitions_reach_execute(self):
        cases = (
            ([], 5, POC.SCENARIOS),
            (["--scenarios", "redirect", "--repetitions", "1"], 1, ("redirect",)),
            (["--scenarios", "range", "drop-once", "range", "--repetitions", "2"],
             2, ("range", "drop-once")),
        )
        for options, repetitions, scenarios in cases:
            with self.subTest(options=options), TemporaryDirectory() as temporary:
                host = Path(temporary) / "host"
                run = Path(temporary) / "run"
                with patch.object(POC, "execute") as execute:
                    POC.main(["--host", str(host), "--run", str(run)] + options)
                execute.assert_called_once_with(host.resolve(), run.resolve(),
                                                repetitions, scenarios)

    def test_invalid_selection_fails_before_creating_run(self):
        for options in (["--scenarios"], ["--scenarios", "unknown"],
                        ["--repetitions", "0"]):
            with self.subTest(options=options), TemporaryDirectory() as temporary:
                run = Path(temporary) / "run"
                with patch.object(POC, "execute") as execute, redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        POC.main(["--host", temporary, "--run", str(run)] + options)
                self.assertEqual(error.exception.code, 2)
                execute.assert_not_called()
                self.assertFalse(run.exists())


if __name__ == "__main__":
    unittest.main()
