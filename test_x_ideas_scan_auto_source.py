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

    def test_cdp_unavailable_is_account_failure_not_batch_guard(self):
        self.assertFalse(scan._is_cdp_guard_error("unavailable: Page guard detected: unavailable"))
        self.assertFalse(scan._is_cdp_guard_error("account_unavailable: This account is unavailable"))
        self.assertFalse(scan._is_cdp_guard_error("no_visible_timeline: No visible timeline items found"))
        self.assertTrue(scan._is_cdp_guard_error("login_required: Page guard detected: login_required"))
        self.assertTrue(scan._is_cdp_guard_error("challenge_required: Page guard detected: challenge_required"))
        self.assertTrue(scan._is_cdp_guard_error("rate_limited: Page guard detected: rate_limited"))

    def test_scan_batch_failed_uses_limited_account_set(self):
        scanned = [f"acct{i}" for i in range(100)]
        all_failed = list(scanned)
        one_ok = scanned[1:]
        self.assertTrue(scan._scan_batch_failed(all_failed, scanned))
        self.assertFalse(scan._scan_batch_failed(one_ok, scanned))
        self.assertTrue(scan._scan_batch_failed([], []))
        self.assertFalse(scan._scan_batch_failed(all_failed, scanned * 2))


if __name__ == "__main__":
    unittest.main()
