from browser_cdp_session import ChromeCDPSession


def test_ensure_page_target_skips_when_page_exists(monkeypatch):
    session = ChromeCDPSession()
    calls = []

    monkeypatch.setattr(
        session,
        "_fetch_cdp_targets",
        lambda: [{"type": "page", "url": "about:blank"}],
    )
    monkeypatch.setattr(session, "_create_background_page_target", lambda: calls.append("create"))

    assert session._ensure_page_target_for_patchright() is True
    assert calls == []


def test_ensure_page_target_creates_background_page_when_missing(monkeypatch):
    session = ChromeCDPSession()
    calls = []
    state = {"created": False}

    def fake_fetch_targets():
        if state["created"]:
            return [{"type": "page", "url": "about:blank"}]
        return [{"type": "service_worker"}]

    def fake_create_target():
        calls.append("create")
        state["created"] = True
        return True

    monkeypatch.setattr(session, "_fetch_cdp_targets", fake_fetch_targets)
    monkeypatch.setattr(session, "_create_background_page_target", fake_create_target)

    assert session._ensure_page_target_for_patchright() is True
    assert calls == ["create"]
