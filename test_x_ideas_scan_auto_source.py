import unittest
from unittest.mock import patch

import xinfo.x_ideas_scan as scan


class XIdeasScanAutoSourceTest(unittest.TestCase):
    def test_auto_source_uses_rss_when_probe_succeeds(self):
        with (
            patch.object(scan, "DATA_SOURCE", "auto"),
            patch.object(scan, "NITTER_INSTANCES", ["https://nitter.test"]),
            patch.object(scan, "RSSHUB_INSTANCES", []),
            patch.object(scan, "log", lambda *_args, **_kwargs: None),
            patch.object(scan, "fetch_rss", lambda _username, _instance: b"<?xml version='1.0'?><rss><channel></channel></rss>"),
        ):
            self.assertEqual("rss", scan.resolve_effective_source())

    def test_auto_source_switches_to_cdp_on_instance_failure(self):
        def fail_rss(_username, _instance):
            raise RuntimeError("HTTP 200 empty body from https://nitter.test/sama/rss")

        with (
            patch.object(scan, "DATA_SOURCE", "auto"),
            patch.object(scan, "NITTER_INSTANCES", ["https://nitter.test"]),
            patch.object(scan, "RSSHUB_INSTANCES", []),
            patch.object(scan, "log", lambda *_args, **_kwargs: None),
            patch.object(scan, "fetch_rss", fail_rss),
        ):
            self.assertEqual("cdp", scan.resolve_effective_source())

    def test_effective_cdp_source_does_not_call_rss_per_account(self):
        def fail_if_called(*_args, **_kwargs):
            raise AssertionError("RSS should not be called when effective source is cdp")

        with (
            patch.object(scan, "EFFECTIVE_SOURCE", "cdp"),
            patch.object(scan, "fetch_rss", fail_if_called),
            patch.object(scan, "fetch_cdp_profile", lambda _username: [
                {
                    "title": "hello",
                    "link": "https://x.com/sama/status/123",
                    "pub_date": "2026-08-22T00:00:00.000Z",
                    "description": "hello",
                }
            ]),
        ):
            items, error = scan.fetch_with_fallback("sama", {})

        self.assertIsNone(error)
        self.assertEqual("https://x.com/sama/status/123", items[0]["link"])


if __name__ == "__main__":
    unittest.main()
