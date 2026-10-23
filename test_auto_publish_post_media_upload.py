"""Unit tests for local large-media CDP attach (no ≥50MiB byte transfer)."""

from pathlib import Path

import pytest

from auto_publish_post import (
    media_upload_timeout_ms,
    set_local_file_input_files,
    upload_post_media,
)


def test_media_upload_timeout_scales_with_size(tmp_path):
    small = tmp_path / "small.bin"
    small.write_bytes(b"x" * 1024)

    large = tmp_path / "large.bin"
    # Sparse-ish: write enough to report ~60MiB without filling disk heavily.
    with large.open("wb") as handle:
        handle.truncate(60 * 1024 * 1024)

    small_ms = media_upload_timeout_ms([str(small)])
    large_ms = media_upload_timeout_ms([str(large)])

    assert 60_000 <= small_ms < 65_000
    assert large_ms > small_ms
    assert large_ms == min(300_000, int(60_000 + 60 * 2_000))
    assert large_ms <= 300_000


def test_media_upload_timeout_caps_at_five_minutes(tmp_path):
    huge = tmp_path / "huge.bin"
    with huge.open("wb") as handle:
        handle.truncate(200 * 1024 * 1024)

    assert media_upload_timeout_ms([str(huge)]) == 300_000


class FakeCdp:
    def __init__(self):
        self.calls = []
        self.detached = False

    def send(self, method, params=None):
        self.calls.append((method, params or {}))
        if method == "DOM.getDocument":
            return {"root": {"nodeId": 1}}
        if method == "DOM.querySelector":
            return {"nodeId": 42}
        if method == "DOM.setFileInputFiles":
            return {}
        raise AssertionError(f"unexpected CDP method: {method}")

    def detach(self):
        self.detached = True


class FakeContext:
    def __init__(self, cdp):
        self.cdp = cdp

    def new_cdp_session(self, page):
        return self.cdp


class FakePage:
    def __init__(self, cdp, *, files_ready_after=0, preview_ready_after=0):
        self.context = FakeContext(cdp)
        self.files_ready_after = files_ready_after
        self.preview_ready_after = preview_ready_after
        self.polls = 0
        self.timeouts = []

    def query_selector(self, selector):
        return object()

    def eval_on_selector(self, selector, script):
        self.polls += 1
        if self.polls > self.files_ready_after:
            return 1
        return 0

    def evaluate(self, script):
        if self.polls > self.preview_ready_after:
            return 1
        return 0

    def wait_for_timeout(self, ms):
        self.timeouts.append(ms)


def test_set_local_file_input_files_uses_cdp_paths_only(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake-video")
    cdp = FakeCdp()
    page = FakePage(cdp)

    set_local_file_input_files(page, 'input[type="file"]', [str(video)])

    methods = [name for name, _ in cdp.calls]
    assert methods == ["DOM.getDocument", "DOM.querySelector", "DOM.setFileInputFiles"]
    set_call = cdp.calls[-1]
    assert set_call[1]["nodeId"] == 42
    assert set_call[1]["files"] == [str(video.resolve())]
    assert cdp.detached is True


def test_set_local_file_input_files_rejects_missing_path(tmp_path):
    cdp = FakeCdp()
    page = FakePage(cdp)
    missing = tmp_path / "missing.mp4"

    with pytest.raises(FileNotFoundError):
        set_local_file_input_files(page, 'input[type="file"]', [str(missing)])
    assert cdp.calls == []


def test_upload_post_media_uses_cdp_and_polls_until_ready(tmp_path, monkeypatch):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    cdp = FakeCdp()
    page = FakePage(cdp, files_ready_after=2, preview_ready_after=2)

    monkeypatch.setattr(
        "auto_publish_post.SELECTORS",
        {"file_input": ['input[data-testid="fileInput"]']},
    )
    monkeypatch.setattr("auto_publish_post._activate_chrome_window", lambda: None)
    monkeypatch.setattr("auto_publish_post._pause_for_observation", lambda *a, **k: None)
    monkeypatch.setattr("auto_publish_post._save_debug_artifacts", lambda *a, **k: None)

    assert upload_post_media(page, [str(video)], step_pause_ms=0) is True
    assert any(method == "DOM.setFileInputFiles" for method, _ in cdp.calls)
    assert page.polls >= 3
    assert page.timeouts  # waited between polls before ready


def test_connect_over_cdp_passes_is_local(monkeypatch):
    from browser_cdp_session import ChromeCDPSession

    recorded = {}

    class FakeBrowser:
        contexts = []

        def new_context(self):
            class Ctx:
                pages = []

                def new_page(self):
                    return object()

            return Ctx()

    class FakeChromium:
        def connect_over_cdp(self, endpoint_url, **kwargs):
            recorded["endpoint"] = endpoint_url
            recorded["kwargs"] = kwargs
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

        def stop(self):
            pass

    class FakeSyncPlaywright:
        def start(self):
            return FakePlaywright()

    session = ChromeCDPSession(remote_debugging_port=19222)
    monkeypatch.setattr("browser_cdp_session.sync_playwright", lambda: FakeSyncPlaywright())
    monkeypatch.setattr(session, "_ensure_page_target_for_patchright", lambda: True)

    session._connect_playwright(headless=True)

    assert recorded["endpoint"] == "http://127.0.0.1:19222"
    assert recorded["kwargs"].get("is_local") is True
