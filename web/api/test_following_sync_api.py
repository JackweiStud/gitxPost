from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import sys

sys.path.insert(0, str(Path(__file__).parent))
from server import app


client = TestClient(app)


@patch("server._run_xpost", new_callable=AsyncMock)
def test_following_sync_endpoint_runs_default_command(mock_run_xpost):
    mock_run_xpost.return_value = {
        "ok": True,
        "xlsx_report": "/Users/jackwl/Code/gitcode/gitxPost/xinfo/log/myfollowing.xlsx",
        "json_snapshot": "/Users/jackwl/Code/gitcode/gitxPost/xinfo/log/following/2026-05-20.json",
        "summary": {
            "completion_status": "complete",
            "collected_following_count": 552,
            "expected_following_count": 552,
        },
    }

    response = client.post("/api/radar/following-sync")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["xlsx_report"].endswith("xinfo/log/myfollowing.xlsx")
    mock_run_xpost.assert_awaited_once_with(
        "following-sync",
        "jackaiwison",
        "--timeout",
        "45",
        "--idle-rounds",
        "20",
        timeout=900,
    )
