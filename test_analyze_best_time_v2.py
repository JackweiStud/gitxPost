import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import analyze_best_time_v2 as best_time


def _write_result(path: Path, summary: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"success": True, "summary": summary}, ensure_ascii=False),
        encoding="utf-8",
    )


class AnalyzeBestTimeV2Test(unittest.TestCase):
    def test_load_radar_posts_uses_preview_sample(self):
        with TemporaryDirectory() as tmp:
            result_file = Path(tmp) / "xinfo" / "log" / "day" / "2026-05-21_result.json"
            _write_result(
                result_file,
                {
                    "new_ideas_preview": [
                        {"time": "Wed, 29 Apr 2026 01:00:00 GMT", "account": "a"},
                        {"time": "Wed, 29 Apr 2026 02:00:00 GMT", "account": "b"},
                    ],
                },
            )

            posts, source_stats = best_time.load_radar_posts([result_file])

            self.assertEqual(2, len(posts))
            self.assertEqual("preview", source_stats["source"])
            self.assertEqual(1, source_stats["days_with_posts"])

    def test_europe_us_traffic_score_prioritizes_western_audience(self):
        morning_for_us_evening = best_time.get_europe_us_traffic_score(10, is_dst=True)
        asia_evening_us_sleeping = best_time.get_europe_us_traffic_score(20, is_dst=True)

        self.assertGreater(morning_for_us_evening, asia_evening_us_sleeping)

    def test_final_score_does_not_let_low_competition_override_weak_us_window(self):
        western_overlap_window = best_time.score_release_window(3, 7.0, is_dst=True)
        low_competition_but_weak_us_window = best_time.score_release_window(19, 10.0, is_dst=True)

        self.assertGreater(
            western_overlap_window["final_score"],
            low_competition_but_weak_us_window["final_score"],
        )

    def test_analyze_outputs_daily_recommendations_not_current_recommendation(self):
        with TemporaryDirectory() as tmp:
            result_file = Path(tmp) / "xinfo" / "log" / "day" / "2026-05-21_result.json"
            _write_result(
                result_file,
                {
                    "new_ideas_preview": [
                        {"time": "Wed, 29 Apr 2026 01:00:00 GMT", "account": "a"},
                        {"time": "Wed, 29 Apr 2026 02:00:00 GMT", "account": "b"},
                        {"time": "Wed, 29 Apr 2026 03:00:00 GMT", "account": "c"},
                    ],
                },
            )
            output_file = Path(tmp) / "best_time_analysis_v2.json"

            result = best_time.analyze_radar_posting_times(
                result_files=[result_file],
                output_file=output_file,
            )

            self.assertNotIn("current_recommendation", result)
            self.assertEqual("欧美用户", result["target_audience"])
            self.assertEqual(5, len(result["daily_recommendations"]))
            self.assertTrue(
                all(item["time"].startswith("北京时间 ") for item in result["daily_recommendations"])
            )
            self.assertTrue(output_file.exists())


if __name__ == "__main__":
    unittest.main()
