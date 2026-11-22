#!/usr/bin/env python3
"""Check the fault server and signed-URL redaction without building RAUC."""

import http.client
import importlib.util
from pathlib import Path
import threading
import unittest


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


if __name__ == "__main__":
    unittest.main()
