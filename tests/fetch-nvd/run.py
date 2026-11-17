#!/usr/bin/env python3
"""Offline fixtures for verified NVD snapshots."""

from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import tarfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("fetch_nvd", ROOT / ".github/scripts/fetch-nvd.py")
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)
NOW = int(datetime(2003, 1, 2, tzinfo=timezone.utc).timestamp())


class FeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "current"
        self.responses = {}
        self.calls = []
        self.feed("2002", [{"id": "CVE-1999-0001", "descriptions": []}])
        self.feed("2003", [{"id": "CVE-2003-0001"}])
        self.feed("modified", [{"id": "CVE-1999-0001", "descriptions": [{"value": "new"}]}])

    def feed(self, name, entries, stamp=NOW):
        data = json.dumps({"format": "NVD_CVE", "version": "2.0",
                           "totalResults": len(entries),
                           "vulnerabilities": [{"cve": entry} for entry in entries]}).encode()
        compressed = gzip.compress(data)
        base = fetch.BASE_URL + "nvdcve-2.0-" + name
        meta = {"lastModifiedDate": datetime.fromtimestamp(stamp, timezone.utc).isoformat(),
                "size": len(data), "gzSize": len(compressed),
                "sha256": hashlib.sha256(data).hexdigest()}
        self.responses[base + ".meta"] = "".join(f"{k}:{v}\n" for k, v in meta.items()).encode()
        self.responses[base + ".json.gz"] = compressed

    def retrieve(self, url):
        self.calls.append(url)
        return self.responses[url]

    def refresh(self, now=NOW):
        return fetch.refresh(self.output, now=now, retrieve=self.retrieve)

    def test_missing_cache_bootstraps_and_uses_id_year(self):
        result = self.refresh()
        self.assertEqual(result["mode"], "bootstrap")
        self.assertEqual(result["count"], 2)
        self.assertEqual(fetch.content_identity(self.output), (result["snapshot_id"], 2))
        entry = json.loads(fetch.entry_path(self.output, "CVE-1999-0001").read_text())
        self.assertEqual(entry["descriptions"], [{"value": "new"}])
        self.assertTrue(self.output.is_symlink())

    def test_incremental_empty_diff_keeps_content_and_updates_sync(self):
        original = self.refresh()
        self.calls.clear()
        self.feed("modified", [])
        updated = self.refresh(now=NOW + 60)
        self.assertEqual(updated["snapshot_id"], original["snapshot_id"])
        self.assertEqual(updated["mode"], "incremental")
        self.assertEqual(updated["synced_at"], NOW + 60)
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(all("modified" in url for url in self.calls))

    def test_incremental_upserts_and_preserves_old_entries(self):
        self.refresh()
        self.feed("modified", [{"id": "CVE-2003-0002"}])
        self.assertEqual(self.refresh()["count"], 3)
        self.assertTrue(fetch.entry_path(self.output, "CVE-1999-0001").exists())

    def test_cache_archive_preserves_relative_snapshot_link(self):
        original = self.refresh()
        archive = Path(self.temp.name) / "cache.tar"
        with tarfile.open(archive, "w") as stream:
            stream.add(self.output, arcname="current")
            stream.add(self.output.resolve(), arcname=self.output.resolve().name)
        restored = Path(self.temp.name) / "restored"
        with tarfile.open(archive) as stream:
            stream.extractall(restored, filter="data")
        self.feed("modified", [])
        result = fetch.refresh(restored / "current", now=NOW + 1, retrieve=self.retrieve)
        self.assertEqual(result["snapshot_id"], original["snapshot_id"])

    def test_window_exceeded_rebootstraps(self):
        self.refresh()
        self.calls.clear()
        later = NOW + fetch.SAFE_WINDOW
        self.feed("modified", [], stamp=later)
        result = self.refresh(now=later)
        self.assertEqual(result["mode"], "bootstrap")
        self.assertTrue(any("2002" in url for url in self.calls))

    def assert_preserved_failure(self):
        before = self.output.resolve()
        manifest = (self.output / "manifest.json").read_bytes()
        with self.assertRaises((ValueError, EOFError, OSError, KeyError)):
            self.refresh()
        self.assertEqual(self.output.resolve(), before)
        self.assertEqual((self.output / "manifest.json").read_bytes(), manifest)
        self.assertEqual(len(list(self.output.parent.glob("snapshot-*"))), 1)

    def test_hash_mismatch_never_promotes(self):
        self.refresh()
        key = fetch.BASE_URL + "nvdcve-2.0-modified.meta"
        text = self.responses[key].decode().splitlines()
        text[-1] = "sha256:" + "0" * 64
        self.responses[key] = ("\n".join(text) + "\n").encode()
        self.assert_preserved_failure()

    def test_truncated_gzip_never_promotes(self):
        self.refresh()
        base = fetch.BASE_URL + "nvdcve-2.0-modified"
        self.responses[base + ".json.gz"] = self.responses[base + ".json.gz"][:-8]
        meta = self.responses[base + ".meta"].decode()
        lines = [f"gzSize:{len(self.responses[base + '.json.gz'])}" if line.startswith("gzSize:")
                 else line for line in meta.splitlines()]
        self.responses[base + ".meta"] = ("\n".join(lines) + "\n").encode()
        self.assert_preserved_failure()

    def test_missing_year_does_not_publish_partial_bootstrap(self):
        del self.responses[fetch.BASE_URL + "nvdcve-2.0-2003.json.gz"]
        with self.assertRaises(KeyError):
            self.refresh()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.output.parent.glob("snapshot-*")))

    def test_stale_modified_meta_and_future_time_rejected(self):
        self.refresh()
        self.feed("modified", [], stamp=NOW - 86401)
        self.assert_preserved_failure()
        self.feed("modified", [], stamp=NOW + 301)
        self.assert_preserved_failure()

    def test_corrupted_cache_is_not_silently_accepted(self):
        self.refresh()
        fetch.entry_path(self.output, "CVE-1999-0001").write_text('{"id":"CVE-1999-0001"}')
        with self.assertRaisesRegex(ValueError, "content mismatch"):
            self.refresh()

    def test_invalid_id_and_duplicate_rejected(self):
        for entries in [[{"id": "../../escape"}],
                        [{"id": "CVE-2003-0001"}, {"id": "CVE-2003-0001"}]]:
            self.feed("modified", entries)
            with self.assertRaises(ValueError):
                self.refresh()
            self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
