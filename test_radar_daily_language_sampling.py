from collections import Counter

import xpost


def _item(account: str, idx: int) -> dict:
    return {
        "account": account,
        "title": f"{account} item {idx}",
        "link": f"https://x.com/{account}/status/{idx}",
        "time": f"Tue, 19 May 2026 03:{idx % 60:02d}:00 GMT",
    }


def test_radar_daily_language_sampling_caps_chinese_and_unknown():
    preview = []
    preview.extend(_item("en_author", idx) for idx in range(100))
    preview.extend(_item("cn_author", idx) for idx in range(100, 200))
    preview.extend(_item("unknown_author", idx) for idx in range(200, 300))

    sampled, meta = xpost._sample_radar_daily_preview_by_language(
        preview,
        max_preview=20,
        account_language_profile={
            "en_author": "en",
            "cn_author": "zh",
            "unknown_author": "unknown",
        },
    )

    counts = Counter(item["source_account_language"] for item in sampled)

    assert len(sampled) == 20
    assert counts["en"] == 13
    assert counts["zh"] == 6
    assert counts["unknown"] == 1
    assert meta["target_percent"] == {"en_min": 65, "zh_max": 30, "unknown_max": 5}
    assert meta["selected_counts"] == {"en": 13, "zh": 6, "unknown": 1}


def test_radar_daily_language_sampling_does_not_overfill_chinese_when_english_is_sparse():
    preview = []
    preview.extend(_item("en_author", idx) for idx in range(4))
    preview.extend(_item("cn_author", idx) for idx in range(100, 200))
    preview.extend(_item("unknown_author", idx) for idx in range(200, 300))

    sampled, meta = xpost._sample_radar_daily_preview_by_language(
        preview,
        max_preview=20,
        account_language_profile={
            "en_author": "en",
            "cn_author": "zh",
            "unknown_author": "unknown",
        },
    )

    counts = Counter(item["source_account_language"] for item in sampled)

    assert len(sampled) == 5
    assert counts["en"] == 4
    assert counts["zh"] == 1
    assert counts["unknown"] == 0
    assert meta["selected_counts"] == {"en": 4, "zh": 1, "unknown": 0}


def test_radar_daily_language_sampling_falls_back_to_item_text_without_account_profile():
    preview = [
        {
            "account": "new_en_author",
            "title": "New agent workflow platform launches with durable memory",
            "summary": "Developers can connect GitHub, Slack, and browser automation.",
            "link": "https://x.com/new_en_author/status/1",
        },
        {
            "account": "new_en_author_2",
            "title": "Open source coding agent adds planning and browser tools",
            "summary": "The release improves workflow automation for developers.",
            "link": "https://x.com/new_en_author_2/status/1",
        },
        {
            "account": "new_en_author_3",
            "title": "AI infrastructure startup ships faster model routing",
            "summary": "Teams can reduce latency while keeping observability.",
            "link": "https://x.com/new_en_author_3/status/1",
        },
        {
            "account": "new_cn_author",
            "title": "新的 AI 工作流平台发布",
            "summary": "支持连接 GitHub、Slack 和浏览器自动化。",
            "link": "https://x.com/new_cn_author/status/1",
        },
    ]

    sampled, meta = xpost._sample_radar_daily_preview_by_language(
        preview,
        max_preview=10,
        account_language_profile={},
    )

    assert [item["source_account_language"] for item in sampled] == ["en", "en", "en", "zh"]
    assert meta["input_counts"] == {"en": 3, "zh": 1, "unknown": 0}


def test_radar_daily_language_sampling_keeps_all_items_when_under_limit():
    preview = []
    preview.extend(_item("en_author", idx) for idx in range(7))
    preview.extend(_item("cn_author", idx) for idx in range(100, 103))

    sampled, meta = xpost._sample_radar_daily_preview_by_language(
        preview,
        max_preview=10,
        account_language_profile={
            "en_author": "en",
            "cn_author": "zh",
        },
    )

    assert len(sampled) == len(preview)
    assert [item["link"] for item in sampled] == [item["link"] for item in preview]
    assert meta["strategy"] == "all_preview_with_language_labels"
    assert meta["selected_counts"] == {"en": 7, "zh": 3, "unknown": 0}


def test_radar_daily_language_sampling_caps_chinese_even_when_under_limit():
    preview = []
    preview.extend(_item("en_author", idx) for idx in range(5))
    preview.extend(_item("cn_author", idx) for idx in range(100, 110))

    sampled, meta = xpost._sample_radar_daily_preview_by_language(
        preview,
        max_preview=100,
        account_language_profile={
            "en_author": "en",
            "cn_author": "zh",
        },
    )

    counts = Counter(item["source_account_language"] for item in sampled)

    assert len(sampled) == 7
    assert counts["en"] == 5
    assert counts["zh"] == 2
    assert meta["strategy"] == "account_language_stratified_sampling"


def test_radar_daily_language_sampling_round_robins_accounts_when_over_limit():
    preview = []
    for account in ["en_a", "en_b", "en_c", "en_d"]:
        preview.extend(_item(account, idx) for idx in range(10))

    sampled, meta = xpost._sample_radar_daily_preview_by_language(
        preview,
        max_preview=4,
        account_language_profile={
            "en_a": "en",
            "en_b": "en",
            "en_c": "en",
            "en_d": "en",
        },
    )

    assert [item["account"] for item in sampled] == ["en_a", "en_b", "en_c", "en_d"]
    assert meta["selected_counts"] == {"en": 4, "zh": 0, "unknown": 0}


def test_radar_daily_prompt_states_language_output_quota():
    prompt = xpost._build_radar_daily_prompt(
        {
            "summary": {
                "new_ideas_preview": [
                    {
                        "account": "en_author",
                        "source_account_language": "en",
                        "title": "Agent workflow launch",
                        "link": "https://x.com/en_author/status/1",
                    }
                ],
                "language_sampling": {
                    "target_percent": {"en_min": 65, "zh_max": 30, "unknown_max": 5}
                },
            }
        },
        {"focus": [], "recent_context": [], "ignore": []},
    )

    assert "EN >= 65%" in prompt
    assert "CN <= 30%" in prompt
    assert "unknown <= 5%" in prompt
