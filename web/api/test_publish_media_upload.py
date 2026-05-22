#!/usr/bin/env python3
"""
测试统一媒体上传与 Post 发布附件链路
"""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).parent))
from server import app

client = TestClient(app)


def test_upload_media_accepts_image_and_video():
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    mp4_data = (
        b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41isom'
        b'\x00\x00\x00\x08free\x00\x00\x00\x08mdat'
    )

    image_resp = client.post(
        "/api/upload/media",
        files={"file": ("a.png", io.BytesIO(png_data), "image/png")},
    )
    video_resp = client.post(
        "/api/upload/media",
        files={"file": ("b.mp4", io.BytesIO(mp4_data), "video/mp4")},
    )

    assert image_resp.status_code == 200
    assert video_resp.status_code == 200
    assert image_resp.json()["kind"] == "image"
    assert video_resp.json()["kind"] == "video"
    assert image_resp.json()["url"].startswith("/uploads/")
    assert video_resp.json()["url"].startswith("/uploads/")

    image_url = image_resp.json()["url"]
    video_url = video_resp.json()["url"]
    image_fetch = client.get(image_url)
    video_fetch = client.get(video_url)
    assert image_fetch.status_code == 200
    assert video_fetch.status_code == 200
    assert image_fetch.content == png_data
    assert video_fetch.content == mp4_data


def test_upload_media_rejects_non_media():
    resp = client.post(
        "/api/upload/media",
        files={"file": ("a.txt", io.BytesIO(b"nope"), "text/plain")},
    )

    assert resp.status_code == 400
    assert "只支持图片或视频" in resp.json()["detail"]


def test_publish_post_accepts_media_attachments(monkeypatch):
    calls = []

    async def fake_run_xpost(*args, **kwargs):
        calls.append(args)
        return {"ok": True, "published": True}

    monkeypatch.setattr("server._run_xpost", fake_run_xpost)

    resp = client.post(
        "/api/publish/post",
        json={
            "text": "hello",
            "attachments": [
                {"kind": "image", "path": "/tmp/a.png"},
                {"kind": "video", "path": "/tmp/b.mp4"},
            ],
            "publish": True,
            "scheduled_at": None,
        },
    )

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert calls, "expected _run_xpost to be called"
    assert "--media" in calls[0]
    assert "/tmp/a.png" in calls[0]
    assert "/tmp/b.mp4" in calls[0]


def test_publish_post_still_accepts_images(monkeypatch):
    calls = []

    async def fake_run_xpost(*args, **kwargs):
        calls.append(args)
        return {"ok": True, "published": True}

    monkeypatch.setattr("server._run_xpost", fake_run_xpost)

    resp = client.post(
        "/api/publish/post",
        json={
            "text": "hello",
            "images": ["/tmp/a.png"],
            "publish": True,
            "scheduled_at": None,
        },
    )

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert calls, "expected _run_xpost to be called"
    assert "--images" in calls[0]
    assert "/tmp/a.png" in calls[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
