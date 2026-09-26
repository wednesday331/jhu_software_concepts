"""Tests for the Chrome/GradCafe page-capture workflow."""

import json
import runpy
from pathlib import Path

import pytest

import capture_page


class FakeResponse:
    """Fake urllib response."""

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(
            self.payload
        ).encode("utf-8")


class FakeSocket:
    """Fake Chrome DevTools websocket."""

    def __init__(self, responses):
        self.responses = iter(responses)
        self.sent = []
        self.closed = False

    def send(self, message):
        self.sent.append(
            json.loads(message)
        )

    def recv(self):
        return json.dumps(
            next(self.responses)
        )

    def close(self):
        self.closed = True


@pytest.mark.integration
def test_find_chrome_returns_existing_path(
    monkeypatch,
    tmp_path,
):
    """The first existing Chrome executable should be returned."""

    missing = tmp_path / "missing.exe"
    existing = tmp_path / "chrome.exe"

    existing.write_text(
        "",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        capture_page,
        "CHROME_PATHS",
        [
            missing,
            existing,
        ],
    )

    assert (
        capture_page._find_chrome()
        == existing
    )


@pytest.mark.integration
def test_find_chrome_raises_when_missing(
    monkeypatch,
    tmp_path,
):
    """A clear exception should be raised when Chrome cannot be found."""

    monkeypatch.setattr(
        capture_page,
        "CHROME_PATHS",
        [
            tmp_path / "missing.exe",
        ],
    )

    with pytest.raises(
        FileNotFoundError,
        match="Google Chrome could not be found",
    ):
        capture_page._find_chrome()


@pytest.mark.integration
def test_start_chrome(
    monkeypatch,
    tmp_path,
    capsys,
):
    """Chrome should start with the required debugging arguments."""

    chrome = tmp_path / "chrome.exe"
    profile = tmp_path / "profile"

    monkeypatch.setattr(
        capture_page,
        "_find_chrome",
        lambda: chrome,
    )

    monkeypatch.setattr(
        capture_page,
        "PROFILE_FOLDER",
        profile,
    )

    commands = []

    monkeypatch.setattr(
        capture_page.subprocess,
        "Popen",
        lambda command:
            commands.append(command),
    )

    sleeps = []

    monkeypatch.setattr(
        capture_page.time,
        "sleep",
        lambda seconds:
            sleeps.append(seconds),
    )

    capture_page._start_chrome()

    command = commands[0]

    assert command[0] == str(chrome)

    assert (
        f"--remote-debugging-port="
        f"{capture_page.DEBUG_PORT}"
        in command
    )

    assert (
        f"--user-data-dir="
        f"{profile.resolve()}"
        in command
    )

    assert (
        "--remote-allow-origins="
        "http://127.0.0.1:9222"
        in command
    )

    assert (
        command[-1]
        == (
            f"{capture_page.BASE_URL}"
            "/survey/"
        )
    )

    assert sleeps == [3]

    assert (
        "Starting a separate Chrome"
        in capsys.readouterr().out
    )


@pytest.mark.integration
def test_get_tabs(monkeypatch):
    """Chrome debugging-tab JSON should be decoded."""

    expected = [
        {
            "url":
                "https://example.com"
        }
    ]

    captured = {}

    def fake_urlopen(
        url,
        timeout,
    ):
        captured["url"] = url
        captured["timeout"] = timeout

        return FakeResponse(
            expected
        )

    monkeypatch.setattr(
        capture_page,
        "urlopen",
        fake_urlopen,
    )

    assert (
        capture_page._get_tabs()
        == expected
    )

    assert captured == {
        "url":
            "http://127.0.0.1:9222/json",
        "timeout":
            5,
    }


@pytest.mark.integration
def test_find_gradcafe_tab(
    monkeypatch,
):
    """The GradCafe survey tab should be selected."""

    expected = {
        "url":
            "https://www.thegradcafe.com/"
            "survey/?page=1"
    }

    monkeypatch.setattr(
        capture_page,
        "_get_tabs",
        lambda: [
            {
                "url":
                    "https://example.com"
            },
            expected,
        ],
    )

    assert (
        capture_page._find_gradcafe_tab()
        == expected
    )


@pytest.mark.integration
def test_find_gradcafe_tab_returns_none(
    monkeypatch,
):
    """Missing/non-GradCafe tabs should return None."""

    monkeypatch.setattr(
        capture_page,
        "_get_tabs",
        lambda: [
            {
                "title":
                    "No URL"
            },
            {
                "url":
                    "https://example.com"
            },
        ],
    )

    assert (
        capture_page._find_gradcafe_tab()
        is None
    )


@pytest.mark.integration
def test_wait_for_gradcafe_tab_retries(
    monkeypatch,
):
    """Temporary exceptions and missing tabs should be retried."""

    values = iter(
        [
            RuntimeError(
                "temporary"
            ),
            None,
            {
                "url":
                    "survey"
            },
        ]
    )

    def fake_find():
        value = next(values)

        if isinstance(
            value,
            Exception,
        ):
            raise value

        return value

    times = iter(
        [
            0,
            0.1,
            0.2,
            0.3,
        ]
    )

    monkeypatch.setattr(
        capture_page,
        "_find_gradcafe_tab",
        fake_find,
    )

    monkeypatch.setattr(
        capture_page.time,
        "time",
        lambda: next(times),
    )

    monkeypatch.setattr(
        capture_page.time,
        "sleep",
        lambda _seconds: None,
    )

    result = (
        capture_page
        ._wait_for_gradcafe_tab(
            timeout=1,
            poll_interval=0,
        )
    )

    assert result == {
        "url":
            "survey"
    }


@pytest.mark.integration
def test_wait_for_gradcafe_tab_timeout(
    monkeypatch,
):
    """The tab wait should return None after its timeout."""

    times = iter(
        [
            0,
            0.1,
            1.1,
        ]
    )

    monkeypatch.setattr(
        capture_page,
        "_find_gradcafe_tab",
        lambda: None,
    )

    monkeypatch.setattr(
        capture_page.time,
        "time",
        lambda: next(times),
    )

    monkeypatch.setattr(
        capture_page.time,
        "sleep",
        lambda _seconds: None,
    )

    assert (
        capture_page
        ._wait_for_gradcafe_tab(
            timeout=1,
            poll_interval=0,
        )
        is None
    )


@pytest.mark.integration
def test_send_cdp_with_and_without_params(
    monkeypatch,
):
    """CDP commands should send JSON and close their sockets."""

    first_socket = FakeSocket(
        [
            {
                "id": 99,
            },
            {
                "id": 1,
                "result":
                    "first",
            },
        ]
    )

    second_socket = FakeSocket(
        [
            {
                "id": 1,
                "result":
                    "second",
            },
        ]
    )

    sockets = iter(
        [
            first_socket,
            second_socket,
        ]
    )

    calls = []

    def fake_connection(
        url,
        **kwargs,
    ):
        calls.append(
            (
                url,
                kwargs,
            )
        )

        return next(sockets)

    monkeypatch.setattr(
        capture_page.websocket,
        "create_connection",
        fake_connection,
    )

    tab = {
        "webSocketDebuggerUrl":
            "ws://debug"
    }

    result = capture_page._send_cdp(
        tab,
        "Test.method",
        {
            "value":
                1,
        },
    )

    assert (
        result["result"]
        == "first"
    )

    assert first_socket.sent == [
        {
            "id":
                1,
            "method":
                "Test.method",
            "params":
                {
                    "value":
                        1,
                },
        }
    ]

    assert first_socket.closed is True

    result = capture_page._send_cdp(
        tab,
        "Other.method",
    )

    assert (
        result["result"]
        == "second"
    )

    assert second_socket.sent == [
        {
            "id":
                1,
            "method":
                "Other.method",
        }
    ]

    assert second_socket.closed is True

    assert (
        calls[0][1]["origin"]
        == "http://127.0.0.1:9222"
    )

    assert (
        calls[0][1]["timeout"]
        == 10
    )


@pytest.mark.integration
def test_send_cdp_closes_after_error(
    monkeypatch,
):
    """The websocket must close even if receiving fails."""

    class BrokenSocket:
        def __init__(self):
            self.closed = False

        def send(self, _message):
            pass

        def recv(self):
            raise RuntimeError(
                "recv failed"
            )

        def close(self):
            self.closed = True

    socket = BrokenSocket()

    monkeypatch.setattr(
        capture_page.websocket,
        "create_connection",
        lambda *args, **kwargs:
            socket,
    )

    with pytest.raises(
        RuntimeError,
        match="recv failed",
    ):
        capture_page._send_cdp(
            {
                "webSocketDebuggerUrl":
                    "ws://debug"
            },
            "Test.method",
        )

    assert socket.closed is True


@pytest.mark.integration
def test_capture_html_retries_then_succeeds(
    monkeypatch,
):
    """Temporary empty Runtime.evaluate responses should be retried."""

    responses = iter(
        [
            {
                "result":
                    {
                        "result":
                            {}
                    }
            },
            {
                "result":
                    {
                        "result":
                            {
                                "value":
                                    "<html>ok</html>"
                            }
                    }
            },
        ]
    )

    monkeypatch.setattr(
        capture_page,
        "_send_cdp",
        lambda *args, **kwargs:
            next(responses),
    )

    sleeps = []

    monkeypatch.setattr(
        capture_page.time,
        "sleep",
        lambda seconds:
            sleeps.append(seconds),
    )

    result = capture_page._capture_html(
        {},
        retries=2,
        retry_delay=0.25,
    )

    assert (
        result
        == "<html>ok</html>"
    )

    assert sleeps == [0.25]


@pytest.mark.integration
def test_capture_html_raises_after_errors(
    monkeypatch,
):
    """Repeated CDP errors should produce a final RuntimeError."""

    def fail(
        *args,
        **kwargs,
    ):
        raise ValueError(
            "temporary"
        )

    monkeypatch.setattr(
        capture_page,
        "_send_cdp",
        fail,
    )

    monkeypatch.setattr(
        capture_page.time,
        "sleep",
        lambda _seconds: None,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Could not capture page HTML "
            "after 2 attempts"
        ),
    ) as exc_info:
        capture_page._capture_html(
            {},
            retries=2,
            retry_delay=0,
        )

    assert isinstance(
        exc_info.value.__cause__,
        ValueError,
    )


@pytest.mark.integration
def test_navigate(monkeypatch):
    """Page navigation should use Page.navigate."""

    calls = []

    monkeypatch.setattr(
        capture_page,
        "_send_cdp",
        lambda *args:
            calls.append(args),
    )

    tab = {
        "id":
            1
    }

    capture_page._navigate(
        tab,
        "https://example.com/next",
    )

    assert calls == [
        (
            tab,
            "Page.navigate",
            {
                "url":
                    "https://example.com/next"
            },
        )
    ]


@pytest.mark.analysis
def test_get_result_urls():
    """Result URLs should be extracted and deduplicated."""

    html = """
    <a href="/result/123">One</a>
    <a href="/result/123">Duplicate</a>
    <a href="/result/456">Two</a>
    """

    assert (
        capture_page._get_result_urls(
            html
        )
        == {
            (
                f"{capture_page.BASE_URL}"
                "/result/123"
            ),
            (
                f"{capture_page.BASE_URL}"
                "/result/456"
            ),
        }
    )


@pytest.mark.integration
def test_next_filename(
    monkeypatch,
    tmp_path,
):
    """The next survey filename should follow the highest existing number."""

    monkeypatch.chdir(
        tmp_path
    )

    assert (
        capture_page._next_filename()
        == Path(
            "survey_page_1.html"
        )
    )

    (
        tmp_path
        / "survey_page.html"
    ).write_text(
        "",
        encoding="utf-8",
    )

    (
        tmp_path
        / "survey_page_7.html"
    ).write_text(
        "",
        encoding="utf-8",
    )

    (
        tmp_path
        / "survey_page_bad.html"
    ).write_text(
        "",
        encoding="utf-8",
    )

    assert (
        capture_page._next_filename()
        == Path(
            "survey_page_8.html"
        )
    )


@pytest.mark.analysis
@pytest.mark.parametrize(
    (
        "html",
        "expected",
    ),
    [
        (
            "<html></html>",
            None,
        ),
        (
            (
                '<a href="/survey?cursor=abc'
                '&amp;x=1">Next</a>'
            ),
            (
                "https://www.thegradcafe.com/"
                "survey?cursor=abc&x=1"
            ),
        ),
        (
            (
                '<a href="survey?cursor=abc">'
                "Next</a>"
            ),
            (
                "https://www.thegradcafe.com/"
                "survey?cursor=abc"
            ),
        ),
        (
            (
                '<a href="https://www.thegradcafe.com/'
                'survey?cursor=abc">Next</a>'
            ),
            (
                "https://www.thegradcafe.com/"
                "survey?cursor=abc"
            ),
        ),
    ],
)
def test_find_next_url(
    html,
    expected,
):
    """Cursor links should become usable next-page URLs."""

    assert (
        capture_page._find_next_url(
            html
        )
        == expected
    )


@pytest.mark.analysis
def test_looks_blocked():
    """Known verification text should be detected."""

    assert (
        capture_page._looks_blocked(
            "Please VERIFY YOU ARE HUMAN"
        )
        is True
    )

    assert (
        capture_page._looks_blocked(
            "Ordinary applicant results"
        )
        is False
    )


@pytest.mark.integration
def test_wait_for_results_prefers_real_results(
    monkeypatch,
):
    """Applicant links should win even if Cloudflare strings remain."""

    html = (
        '<a href="/result/123">'
        "Applicant</a> cf-chl"
    )

    monkeypatch.setattr(
        capture_page,
        "_capture_html",
        lambda _tab:
            html,
    )

    assert (
        capture_page._wait_for_results(
            {}
        )
        == html
    )


@pytest.mark.integration
def test_wait_for_results_returns_block_page(
    monkeypatch,
):
    """Verification pages should be returned immediately."""

    html = (
        "Verification required"
    )

    monkeypatch.setattr(
        capture_page,
        "_capture_html",
        lambda _tab:
            html,
    )

    assert (
        capture_page._wait_for_results(
            {}
        )
        == html
    )


@pytest.mark.integration
def test_wait_for_results_timeout(
    monkeypatch,
):
    """Timeout should perform one final HTML capture."""

    captures = iter(
        [
            "waiting",
            "final",
        ]
    )

    monkeypatch.setattr(
        capture_page,
        "_capture_html",
        lambda _tab:
            next(captures),
    )

    times = iter(
        [
            0,
            0.5,
            1.1,
        ]
    )

    monkeypatch.setattr(
        capture_page.time,
        "time",
        lambda:
            next(times),
    )

    monkeypatch.setattr(
        capture_page.time,
        "sleep",
        lambda _seconds:
            None,
    )

    assert (
        capture_page
        ._wait_for_results(
            {},
            timeout=1,
        )
        == "final"
    )


@pytest.mark.analysis
def test_append_page_records(
    monkeypatch,
):
    """Only unseen records with real URLs should be appended."""

    monkeypatch.setattr(
        capture_page,
        "parse_survey_page",
        lambda _html: [
            {
                "url":
                    "https://example.com/1"
            },
            {
                "url":
                    "https://example.com/2"
            },
            {
                "url":
                    ""
            },
        ],
    )

    data = []

    existing_urls = {
        "https://example.com/1"
    }

    result = (
        capture_page
        ._append_page_records(
            "html",
            data,
            existing_urls,
        )
    )

    assert result == (
        3,
        1,
    )

    assert data == [
        {
            "url":
                "https://example.com/2"
        }
    ]


@pytest.mark.integration
def test_capture_pages_web_mode_requires_tab(
    monkeypatch,
):
    """Web mode should fail if the user's Chrome tab is unavailable."""

    monkeypatch.setattr(
        capture_page,
        "_find_gradcafe_tab",
        lambda:
            None,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Open your GradCafe Chrome "
            "capture window"
        ),
    ):
        capture_page.capture_pages(
            web_mode=True
        )


@pytest.mark.integration
def test_capture_pages_handles_initial_tab_exception(
    monkeypatch,
):
    """Debugging-port errors should behave like a missing tab."""

    def fail():
        raise RuntimeError(
            "debugging unavailable"
        )

    monkeypatch.setattr(
        capture_page,
        "_find_gradcafe_tab",
        fail,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Open your GradCafe Chrome "
            "capture window"
        ),
    ):
        capture_page.capture_pages(
            web_mode=True
        )


@pytest.mark.integration
def test_capture_pages_web_mode_requires_results(
    monkeypatch,
):
    """Web mode should stop when applicant results are not visible."""

    tab = {
        "url":
            (
                "https://www.thegradcafe.com/"
                "survey/"
            )
    }

    monkeypatch.setattr(
        capture_page,
        "_find_gradcafe_tab",
        lambda:
            tab,
    )

    monkeypatch.setattr(
        capture_page,
        "_wait_for_results",
        lambda _tab, timeout=10:
            "verification required",
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "applicant results "
            "are not visible"
        ),
    ):
        capture_page.capture_pages(
            web_mode=True
        )


@pytest.mark.integration
def test_capture_pages_manual_start_then_missing(
    monkeypatch,
    capsys,
):
    """Manual mode should start Chrome and stop if the tab is still missing."""

    findings = iter(
        [
            None,
            None,
        ]
    )

    monkeypatch.setattr(
        capture_page,
        "_find_gradcafe_tab",
        lambda:
            next(findings),
    )

    started = []

    monkeypatch.setattr(
        capture_page,
        "_start_chrome",
        lambda:
            started.append(True),
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt:
            "",
    )

    capture_page.capture_pages(
        web_mode=False
    )

    assert started == [True]

    assert (
        "Could not find the GradCafe survey tab."
        in capsys.readouterr().out
    )


@pytest.mark.integration
def test_capture_pages_existing_manual_tab(
    monkeypatch,
    capsys,
):
    """Manual mode should reuse an already-open compatible Chrome tab."""

    tab = {
        "url":
            (
                "https://www.thegradcafe.com/"
                "survey/"
            )
    }

    monkeypatch.setattr(
        capture_page,
        "_find_gradcafe_tab",
        lambda:
            tab,
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt:
            "",
    )

    monkeypatch.setattr(
        capture_page,
        "load_data",
        lambda:
            [],
    )

    monkeypatch.setattr(
        capture_page,
        "_wait_for_gradcafe_tab",
        lambda:
            None,
    )

    capture_page.capture_pages(
        web_mode=False
    )

    output = (
        capsys.readouterr().out
    )

    assert (
        "Found the existing GradCafe Chrome window."
        in output
    )

    assert (
        "The GradCafe tab could not be found "
        "after retrying. Stopping."
        in output
    )


@pytest.mark.integration
def test_capture_pages_blocked_page(
    monkeypatch,
    capsys,
):
    """The workflow should stop instead of continuing through verification."""

    tab = {
        "url":
            (
                "https://www.thegradcafe.com/"
                "survey/"
            )
    }

    monkeypatch.setattr(
        capture_page,
        "_find_gradcafe_tab",
        lambda:
            tab,
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt:
            "",
    )

    monkeypatch.setattr(
        capture_page,
        "load_data",
        lambda:
            [],
    )

    monkeypatch.setattr(
        capture_page,
        "_wait_for_gradcafe_tab",
        lambda:
            tab,
    )

    monkeypatch.setattr(
        capture_page,
        "_wait_for_results",
        lambda *args, **kwargs:
            "verification required",
    )

    monkeypatch.setattr(
        capture_page,
        "MAX_PAGES",
        1,
    )

    capture_page.capture_pages(
        web_mode=False
    )

    assert (
        "GradCafe appears to be requesting "
        "verification"
        in capsys.readouterr().out
    )


@pytest.mark.integration
def test_capture_pages_no_results(
    monkeypatch,
    capsys,
):
    """The workflow should stop on an ordinary page with no results."""

    tab = {
        "url":
            (
                "https://www.thegradcafe.com/"
                "survey/"
            )
    }

    monkeypatch.setattr(
        capture_page,
        "_find_gradcafe_tab",
        lambda:
            tab,
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt:
            "",
    )

    monkeypatch.setattr(
        capture_page,
        "load_data",
        lambda:
            [],
    )

    monkeypatch.setattr(
        capture_page,
        "_wait_for_gradcafe_tab",
        lambda:
            tab,
    )

    monkeypatch.setattr(
        capture_page,
        "_wait_for_results",
        lambda *args, **kwargs:
            "ordinary empty page",
    )

    monkeypatch.setattr(
        capture_page,
        "MAX_PAGES",
        1,
    )

    capture_page.capture_pages(
        web_mode=False
    )

    assert (
        "No applicant results were found. Stopping."
        in capsys.readouterr().out
    )


@pytest.mark.integration
def test_capture_pages_checkpoint(
    monkeypatch,
    tmp_path,
    capsys,
):
    """New pages should save HTML and checkpoint accumulated JSON."""

    monkeypatch.chdir(
        tmp_path
    )

    tab = {
        "url":
            (
                "https://www.thegradcafe.com/"
                "survey/"
            )
    }

    html = (
        '<a href="/result/2">'
        "Result</a>"
    )

    monkeypatch.setattr(
        capture_page,
        "_find_gradcafe_tab",
        lambda:
            tab,
    )

    monkeypatch.setattr(
        capture_page,
        "_wait_for_gradcafe_tab",
        lambda:
            tab,
    )

    monkeypatch.setattr(
        capture_page,
        "_wait_for_results",
        lambda *args, **kwargs:
            html,
    )

    monkeypatch.setattr(
        capture_page,
        "load_data",
        lambda: [
            {
                "url":
                    (
                        f"{capture_page.BASE_URL}"
                        "/result/1"
                    )
            }
        ],
    )

    monkeypatch.setattr(
        capture_page,
        "parse_survey_page",
        lambda _html: [
            {
                "url":
                    (
                        f"{capture_page.BASE_URL}"
                        "/result/2"
                    )
            }
        ],
    )

    saves = []

    monkeypatch.setattr(
        capture_page,
        "save_data",
        lambda data:
            saves.append(
                list(data)
            ),
    )

    monkeypatch.setattr(
        capture_page,
        "MAX_PAGES",
        1,
    )

    monkeypatch.setattr(
        capture_page,
        "SAVE_EVERY_PAGES",
        1,
    )

    capture_page.capture_pages(
        web_mode=True
    )

    saved_html = (
        tmp_path
        / "survey_page_1.html"
    )

    assert (
        saved_html.read_text(
            encoding="utf-8"
        )
        == html
    )

    assert len(saves) == 1
    assert len(saves[0]) == 2

    output = (
        capsys.readouterr().out
    )

    assert (
        "Checkpoint saved: 2 total records"
        in output
    )

    assert (
        "Could not locate the normal next-page URL."
        in output
    )

    assert (
        "New HTML pages captured: 1"
        in output
    )


@pytest.mark.integration
def test_capture_pages_final_checkpoint(
    monkeypatch,
    tmp_path,
    capsys,
):
    """Unsaved pages should always be persisted by finally."""

    monkeypatch.chdir(
        tmp_path
    )

    tab = {
        "url":
            (
                "https://www.thegradcafe.com/"
                "survey/"
            )
    }

    html = (
        '<a href="/result/2">'
        "Result</a>"
    )

    monkeypatch.setattr(
        capture_page,
        "_find_gradcafe_tab",
        lambda:
            tab,
    )

    monkeypatch.setattr(
        capture_page,
        "_wait_for_gradcafe_tab",
        lambda:
            tab,
    )

    monkeypatch.setattr(
        capture_page,
        "_wait_for_results",
        lambda *args, **kwargs:
            html,
    )

    monkeypatch.setattr(
        capture_page,
        "load_data",
        lambda:
            [],
    )

    monkeypatch.setattr(
        capture_page,
        "parse_survey_page",
        lambda _html: [
            {
                "url":
                    (
                        f"{capture_page.BASE_URL}"
                        "/result/2"
                    )
            }
        ],
    )

    saves = []

    monkeypatch.setattr(
        capture_page,
        "save_data",
        lambda data:
            saves.append(
                list(data)
            ),
    )

    monkeypatch.setattr(
        capture_page,
        "MAX_PAGES",
        1,
    )

    monkeypatch.setattr(
        capture_page,
        "SAVE_EVERY_PAGES",
        25,
    )

    capture_page.capture_pages(
        web_mode=True
    )

    assert len(saves) == 1

    assert (
        "Final checkpoint saved: 1 total records"
        in capsys.readouterr().out
    )


@pytest.mark.integration
def test_capture_pages_existing_page_navigates(
    monkeypatch,
    capsys,
):
    """An already-saved page should navigate to the next cursor page."""

    tab = {
        "url":
            (
                "https://www.thegradcafe.com/"
                "survey/"
            )
    }

    existing_url = (
        f"{capture_page.BASE_URL}"
        "/result/1"
    )

    html = """
    <a href="/result/1">Result</a>
    <a href="/survey?cursor=abc">Next</a>
    """

    tab_results = iter(
        [
            tab,
            None,
        ]
    )

    monkeypatch.setattr(
        capture_page,
        "_find_gradcafe_tab",
        lambda:
            tab,
    )

    monkeypatch.setattr(
        capture_page,
        "_wait_for_gradcafe_tab",
        lambda:
            next(tab_results),
    )

    monkeypatch.setattr(
        capture_page,
        "_wait_for_results",
        lambda *args, **kwargs:
            html,
    )

    monkeypatch.setattr(
        capture_page,
        "load_data",
        lambda: [
            {
                "url":
                    existing_url
            }
        ],
    )

    monkeypatch.setattr(
        capture_page,
        "MAX_PAGES",
        2,
    )

    monkeypatch.setattr(
        capture_page.time,
        "sleep",
        lambda _seconds:
            None,
    )

    navigations = []

    monkeypatch.setattr(
        capture_page,
        "_navigate",
        lambda tab_arg, url:
            navigations.append(
                (
                    tab_arg,
                    url,
                )
            ),
    )

    capture_page.capture_pages(
        web_mode=True
    )

    assert navigations == [
        (
            tab,
            (
                f"{capture_page.BASE_URL}"
                "/survey?cursor=abc"
            ),
        )
    ]

    output = (
        capsys.readouterr().out
    )

    assert (
        "This page is already present in "
        "applicant_data.json."
        in output
    )

    assert (
        "Navigating to:"
        in output
    )


@pytest.mark.integration
def test_capture_page_main_entrypoint(
    monkeypatch,
    capsys,
):
    """Executing capture_page.py directly should invoke capture_pages."""

    # runpy re-imports urlopen from urllib.request,
    # so patch the source module itself.
    import urllib.request

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *args, **kwargs:
            FakeResponse([]),
    )

    # Make _find_chrome believe the first configured
    # Chrome path exists.
    monkeypatch.setattr(
        Path,
        "exists",
        lambda _self:
            True,
    )

    monkeypatch.setattr(
        capture_page.subprocess,
        "Popen",
        lambda _command:
            None,
    )

    monkeypatch.setattr(
        capture_page.time,
        "sleep",
        lambda _seconds:
            None,
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt:
            "",
    )

    runpy.run_path(
        capture_page.__file__,
        run_name="__main__",
    )

    assert (
        "Could not find the GradCafe survey tab."
        in capsys.readouterr().out
    )