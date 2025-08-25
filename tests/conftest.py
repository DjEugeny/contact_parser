import os
import re
import imaplib
import builtins
import pytest
from unittest.mock import MagicMock


def pytest_addoption(parser):
    parser.addoption(
        "--e2e",
        action="store_true",
        default=False,
        help="Run e2e/slow tests"
    )


@pytest.fixture(autouse=True)
def skip_slow_tests(request):
    # По умолчанию скипаем долгие/интеграционные тесты, unless --e2e
    slow_mark = request.node.get_closest_marker("slow")
    e2e_mark = request.node.get_closest_marker("e2e")
    is_e2e = request.config.getoption("--e2e")
    if (slow_mark or e2e_mark) and not is_e2e:
        pytest.skip("Skipping slow/e2e test. Use --e2e to run.")


@pytest.fixture(autouse=True)
def mock_time_sleep(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)


@pytest.fixture(autouse=True)
def mock_input(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda *_args, **_kwargs: "")


@pytest.fixture(autouse=True)
def mock_requests_post(monkeypatch):
    class DummyResponse:
        def __init__(self, json_data):
            self._json = json_data
            self.status_code = 200

        def json(self):
            return self._json

        @property
        def text(self):
            return ""

    def fake_post(*_args, **_kwargs):
        # Минимально валидная структура для _make_llm_request -> _parse_llm_response
        return DummyResponse({
            "choices": [
                {
                    "message": {
                        "content": "{\n  \"contacts\": [{\n    \"name\": \"John Doe\",\n    \"email\": \"john@example.com\",\n    \"phone\": \"+1234567890\",\n    \"organization\": \"ACME\",\n    \"confidence\": 0.9\n  }],\n  \"business_context\": \"ok\",\n  \"recommended_actions\": \"ok\"\n}"
                    }
                }
            ]
        })

    monkeypatch.setattr("requests.post", fake_post)


@pytest.fixture(autouse=True)
def mock_imap(monkeypatch):
    class DummyIMAP:
        def __init__(self, *_args, **_kwargs):
            pass

        def login(self, *_args, **_kwargs):
            return "OK", []

        def select(self, *_args, **_kwargs):
            return "OK", []

        def search(self, *_args, **_kwargs):
            return "OK", [b"1 2 3"]

        def fetch(self, *_args, **_kwargs):
            return "OK", [(b"1 (RFC822)", b"Subject: Test\n\nBody")]

        def logout(self):
            return "OK", []

    monkeypatch.setattr(imaplib, "IMAP4", DummyIMAP)
    monkeypatch.setattr(imaplib, "IMAP4_SSL", DummyIMAP)