from auto_publish_post import click_post_button


class FakeButton:
    def __init__(self, disabled_states):
        self.disabled_states = list(disabled_states)
        self.evaluations = 0
        self.clicks = 0

    def evaluate(self, script):
        if "aria-disabled" in script:
            index = min(self.evaluations, len(self.disabled_states) - 1)
            self.evaluations += 1
            return self.disabled_states[index]
        if "scrollIntoView" in script:
            self.clicks += 1
        return None


class FakePage:
    def __init__(self, button):
        self.button = button
        self.timeouts = []
        self.waited = False

    def query_selector(self, selector):
        return self.button

    def wait_for_timeout(self, ms):
        self.timeouts.append(ms)

    def wait_for_function(self, script, timeout=12000):
        self.waited = True
        return True


def test_click_post_button_waits_for_button_to_enable(monkeypatch):
    button = FakeButton([True, True, True, True, True, True, False])
    page = FakePage(button)
    monkeypatch.setattr("auto_publish_post._pause_for_observation", lambda *args, **kwargs: None)

    result = click_post_button(page, publish=True, step_pause_ms=0)

    assert result is True
    assert button.clicks == 1
    assert page.waited is True
    assert page.timeouts, "expected click_post_button to wait while the button is disabled"
