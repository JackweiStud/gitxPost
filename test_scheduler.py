import unittest
from datetime import datetime

import xpost


class SchedulerTimesTest(unittest.TestCase):
    def test_parse_empty_uses_default_three_slots(self):
        self.assertEqual(["09:00", "14:00", "20:00"], xpost._parse_scheduler_times(""))

    def test_parse_single_hour_stays_single(self):
        self.assertEqual(["01:00"], xpost._parse_scheduler_times("1:00"))
        self.assertEqual(["09:00"], xpost._parse_scheduler_times("09:00"))

    def test_parse_dedupes_and_normalizes(self):
        self.assertEqual(
            ["09:00", "14:00", "20:00"],
            xpost._parse_scheduler_times("9:00, 14:00; 20:00, 09:00"),
        )


class SchedulerShouldFullTest(unittest.TestCase):
    times = ["09:00", "14:00", "20:00"]

    def test_midday_incomplete_is_scan_only(self):
        decision = xpost._scheduler_should_full(
            now=datetime(2026, 8, 24, 14, 0),
            scheduled_times=self.times,
            remaining_count=80,
            report_exists=False,
        )
        self.assertFalse(decision["full"])
        self.assertEqual("scan_only", decision["reason"])
        self.assertFalse(decision["last_slot"])

    def test_day_complete_before_last_slot_generates_report(self):
        decision = xpost._scheduler_should_full(
            now=datetime(2026, 8, 24, 14, 5),
            scheduled_times=self.times,
            remaining_count=0,
            report_exists=False,
        )
        self.assertTrue(decision["full"])
        self.assertEqual("day_complete", decision["reason"])

    def test_last_slot_generates_report_even_if_incomplete(self):
        decision = xpost._scheduler_should_full(
            now=datetime(2026, 8, 24, 20, 8),
            scheduled_times=self.times,
            remaining_count=29,
            report_exists=False,
        )
        self.assertTrue(decision["full"])
        self.assertEqual("last_slot", decision["reason"])
        self.assertTrue(decision["last_slot"])

    def test_already_reported_skips_duplicate(self):
        decision = xpost._scheduler_should_full(
            now=datetime(2026, 8, 24, 20, 8),
            scheduled_times=self.times,
            remaining_count=0,
            report_exists=True,
        )
        self.assertFalse(decision["full"])
        self.assertEqual("already_reported", decision["reason"])

    def test_single_0100_slot_is_last_that_calendar_day(self):
        decision = xpost._scheduler_should_full(
            now=datetime(2026, 8, 24, 1, 0),
            scheduled_times=["01:00"],
            remaining_count=129,
            report_exists=False,
        )
        self.assertTrue(decision["full"])
        self.assertEqual("last_slot", decision["reason"])

    def test_last_slot_does_not_cross_midnight(self):
        self.assertTrue(
            xpost._is_last_scheduler_slot(datetime(2026, 8, 24, 23, 50), ["23:40"])
        )
        self.assertFalse(
            xpost._is_last_scheduler_slot(datetime(2026, 8, 25, 0, 10), ["23:40"])
        )
        self.assertFalse(
            xpost._is_last_scheduler_slot(datetime(2026, 8, 24, 15, 0), ["01:00"])
        )

    def test_last_slot_grace_covers_late_start_not_scan_duration(self):
        self.assertTrue(
            xpost._is_last_scheduler_slot(datetime(2026, 8, 24, 21, 30), ["20:00"])
        )
        self.assertFalse(
            xpost._is_last_scheduler_slot(datetime(2026, 8, 24, 21, 31), ["20:00"])
        )

    def test_job_start_at_last_slot_still_reports_after_long_scan_clock(self):
        decision = xpost._scheduler_should_full(
            now=datetime(2026, 8, 24, 20, 0),
            scheduled_times=self.times,
            remaining_count=29,
            report_exists=False,
        )
        self.assertTrue(decision["full"])
        self.assertEqual("last_slot", decision["reason"])

    def test_parse_scheduler_now_accepts_job_start_stamp(self):
        parsed = xpost._parse_scheduler_now("2026-08-24 20:00:05")
        self.assertEqual(datetime(2026, 8, 24, 20, 0, 5), parsed)
        self.assertIsInstance(xpost._parse_scheduler_now(""), datetime)
        with self.assertRaises(ValueError):
            xpost._parse_scheduler_now("20:00")


if __name__ == "__main__":
    unittest.main()
