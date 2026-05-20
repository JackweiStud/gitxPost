from pathlib import Path

import openpyxl

import following_sync


def test_build_comparison_rows_splits_following_and_radar_gaps():
    following = [
        {
            "handle": "Alpha",
            "display_name": "Alpha Labs",
            "bio": "Builds AI tools",
            "profile_url": "https://x.com/Alpha",
        },
        {
            "handle": "@Bravo",
            "display_name": "Bravo",
            "bio": "Chinese AI notes",
            "profile_url": "https://x.com/Bravo",
        },
    ]
    radar_accounts = [
        {"handle": "bravo", "note": "radar note", "status": "active"},
        {"handle": "Charlie", "note": "radar only", "status": "active"},
        {"handle": "Removed", "note": "old", "status": "removed"},
    ]

    result = following_sync.build_comparison(
        following,
        radar_accounts,
        language_by_handle={
            "bravo": {"language_label": "CN"},
            "charlie": {"language_label": "EN"},
        },
        fetched_at="2026-05-20T10:00:00+08:00",
    )

    assert [row["handle"] for row in result["following"]] == ["Alpha", "Bravo"]
    assert [row["handle"] for row in result["radar"]] == ["bravo", "Charlie"]
    assert [row["handle"] for row in result["gap1"]] == ["Alpha"]
    assert [row["handle"] for row in result["gap2"]] == ["Charlie"]
    assert result["summary"]["following_count"] == 2
    assert result["summary"]["radar_active_count"] == 2
    assert result["summary"]["gap1_count"] == 1
    assert result["summary"]["gap2_count"] == 1
    assert result["radar"][0]["language_label"] == "CN"


def test_write_xlsx_report_creates_expected_sheets(tmp_path: Path):
    comparison = {
        "summary": {
            "username": "jackaiwison",
            "fetched_at": "2026-05-20T10:00:00+08:00",
            "expected_following_count": 2,
            "collected_following_count": 2,
            "following_count": 2,
            "radar_active_count": 1,
            "gap1_count": 1,
            "gap2_count": 0,
            "complete": True,
        },
        "following": [
            {
                "data_label": "following",
                "handle": "alpha",
                "display_name": "Alpha",
                "note": "",
                "bio": "bio",
                "profile_url": "https://x.com/alpha",
                "in_following": True,
                "in_radar": False,
                "radar_status": "",
                "language_label": "",
                "source": "x_following",
                "fetched_at": "2026-05-20T10:00:00+08:00",
            }
        ],
        "radar": [],
        "gap1": [],
        "gap2": [],
    }
    out = tmp_path / "myfollowing.xlsx"

    following_sync.write_xlsx_report(comparison, out)

    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == [
        "Summary",
        "Following",
        "Radar",
        "GAP1_Following_Not_Radar",
        "GAP2_Radar_Not_Following",
    ]
    assert wb["Summary"]["A1"].value == "metric"
    assert wb["Summary"]["B2"].value == "jackaiwison"
    assert wb["Following"]["A1"].value == "data_label"
    assert wb["Following"]["B2"].value == "alpha"


def test_collection_complete_is_false_when_limit_stops_before_expected_count():
    assert following_sync.is_collection_complete(
        expected_following_count=None,
        collected_count=546,
        limit=0,
    ) is False

    assert following_sync.is_collection_complete(
        expected_following_count=546,
        collected_count=5,
        limit=5,
    ) is False

    assert following_sync.is_collection_complete(
        expected_following_count=5,
        collected_count=5,
        limit=5,
    ) is True


def test_build_comparison_marks_unknown_expected_as_incomplete_by_default():
    result = following_sync.build_comparison(
        [{"handle": "Alpha"}],
        [],
        fetched_at="2026-05-20T10:00:00+08:00",
    )

    assert result["summary"]["complete"] is False
    assert result["summary"]["completion_status"] == "unknown"


def test_extract_user_rows_from_graphql_payload_reads_nested_legacy_users():
    payload = {
        "data": {
            "user": {
                "result": {
                    "timeline": {
                        "timeline": {
                            "instructions": [
                                {
                                    "entries": [
                                        {
                                            "content": {
                                                "itemContent": {
                                                    "user_results": {
                                                        "result": {
                                                            "legacy": {
                                                                "screen_name": "Alpha",
                                                                "name": "Alpha Labs",
                                                                "description": "Builds tools",
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                }
            }
        }
    }

    rows = following_sync.extract_user_rows_from_graphql_payload(payload)

    assert rows == [
        {
            "handle": "Alpha",
            "display_name": "Alpha Labs",
            "bio": "Builds tools",
            "profile_url": "https://x.com/Alpha",
        }
    ]


def test_extract_user_rows_from_graphql_payload_ignores_non_timeline_legacy_users():
    payload = {
        "data": {
            "user": {
                "result": {
                    "legacy": {
                        "screen_name": "Viewer",
                        "name": "Viewer Account",
                        "description": "Should not be collected",
                    },
                    "timeline": {
                        "timeline": {
                            "instructions": [
                                {
                                    "entries": [
                                        {
                                            "content": {
                                                "itemContent": {
                                                    "user_results": {
                                                        "result": {
                                                            "legacy": {
                                                                "screen_name": "FollowingUser",
                                                                "name": "Following User",
                                                                "description": "Actually followed",
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    },
                }
            }
        }
    }

    rows = following_sync.extract_user_rows_from_graphql_payload(payload)

    assert [row["handle"] for row in rows] == ["FollowingUser"]


def test_following_graphql_url_filter_matches_operation_not_any_query_text():
    assert following_sync.is_following_graphql_url("https://x.com/i/api/graphql/abc/Following?variables={}") is True
    assert following_sync.is_following_graphql_url("https://x.com/i/api/graphql/abc/Followers?cursor=following") is False


def test_merge_account_row_keeps_more_complete_fields_for_same_handle():
    row = following_sync.merge_account_row(
        {"handle": "alpha", "display_name": "alpha", "bio": ""},
        {"handle": "Alpha", "display_name": "Alpha Labs", "bio": "Builds useful AI tools"},
    )

    assert row["handle"] == "alpha"
    assert row["display_name"] == "Alpha Labs"
    assert row["bio"] == "Builds useful AI tools"
