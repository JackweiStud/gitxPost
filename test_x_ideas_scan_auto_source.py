import json
import tempfile
import threading
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
        self.assertFalse(scan._is_cdp_guard_error("timeline_error: Page guard detected: timeline_error"))
        self.assertTrue(scan._is_cdp_guard_error("login_required: Page guard detected: login_required"))
        self.assertTrue(scan._is_cdp_guard_error("challenge_required: Page guard detected: challenge_required"))
        self.assertTrue(scan._is_cdp_guard_error("rate_limited: Page guard detected: rate_limited"))

    def test_cdp_empty_timeline_is_deferred_retryable(self):
        self.assertTrue(scan._is_cdp_deferred_retryable("no_visible_timeline: No visible timeline items found"))
        self.assertTrue(scan._is_cdp_deferred_retryable("timeline_error: Page guard detected: timeline_error"))
        self.assertTrue(scan._is_cdp_deferred_retryable("unavailable: Page guard detected: unavailable"))
        self.assertFalse(scan._is_cdp_deferred_retryable("login_required: Page guard detected: login_required"))
        self.assertFalse(scan._is_cdp_deferred_retryable("challenge_required: Page guard detected: challenge_required"))
        self.assertFalse(scan._is_cdp_deferred_retryable(""))

    def test_same_day_cdp_completed_ignores_smoke_and_lock_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/day_result.json"
            self.assertFalse(scan._same_day_cdp_completed(path))

            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"effective_source": "cdp", "total_accounts": 40, "error_type": None}, handle)
            self.assertTrue(scan._same_day_cdp_completed(path))
            self.assertTrue(scan._should_skip_same_day_cdp("cdp", force=False, result_path=path))
            self.assertFalse(scan._should_skip_same_day_cdp("cdp", force=True, result_path=path))
            self.assertFalse(scan._should_skip_same_day_cdp("rss", force=False, result_path=path))
            self.assertFalse(scan._should_skip_same_day_cdp("cdp", force=False, result_path=path, account_limit=1))

            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"effective_source": "cdp", "total_accounts": 1}, handle)
            self.assertFalse(scan._same_day_cdp_completed(path))

            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"effective_source": "cdp", "total_accounts": 40, "error_type": "radar_scan_already_running"}, handle)
            self.assertFalse(scan._same_day_cdp_completed(path))

    def test_deferred_retry_runs_each_failed_account_once(self):
        calls = []
        stop_scan = threading.Event()

        def scan_one(username, deferred_pass=False):
            calls.append((username, deferred_pass))

        with patch.object(scan, "log", lambda *_args, **_kwargs: None):
            scan._run_cdp_deferred_retry(["a", "b"], scan_one, stop_scan, pause_seconds=0)
            self.assertEqual(calls, [("a", True), ("b", True)])

            calls.clear()
            stop_scan.set()
            scan._run_cdp_deferred_retry(["a", "b"], scan_one, stop_scan, pause_seconds=0)
            self.assertEqual(calls, [])

    def test_scan_batch_failed_uses_limited_account_set(self):
        scanned = [f"acct{i}" for i in range(100)]
        all_failed = list(scanned)
        one_ok = scanned[1:]
        self.assertTrue(scan._scan_batch_failed(all_failed, scanned))
        self.assertFalse(scan._scan_batch_failed(one_ok, scanned))
        self.assertTrue(scan._scan_batch_failed([], []))
        self.assertFalse(scan._scan_batch_failed(all_failed, scanned * 2))

    def test_main_refuses_when_scan_process_already_active(self):
        active = [{"pid": 12345, "ppid": 1, "command": "python xpost.py radar-scan --source auto --limit 100"}]
        with (
            patch.object(scan, "ensure_dirs", lambda: None),
            patch.object(scan, "_active_scan_processes", lambda: active),
            patch.object(scan, "log", lambda *_args, **_kwargs: None),
            patch.object(scan, "_emit_result_json") as print_result,
        ):
            self.assertEqual(2, scan.main())

        result = print_result.call_args.args[0]
        self.assertFalse(result["success"])
        self.assertEqual("radar_scan_already_running", result["error_type"])
        self.assertEqual(active, result["active_processes"])


if __name__ == "__main__":
    unittest.main()
