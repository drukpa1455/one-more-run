import io
import json
import urllib.error

import pytest

from one_more_run import hindsight
from one_more_run.hindsight import Hindsight, HindsightError, from_environment


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_recall_returns_a_bounded_memory_prompt(monkeypatch):
    calls = []

    def urlopen(request, timeout):
        calls.append((request, timeout))
        return Response(
            b'{"results":[{"text":"Momentum failed"},{"text":"LR improved"}]}'
        )

    monkeypatch.setattr(hindsight.urllib.request, "urlopen", urlopen)
    client = Hindsight("https://memory.example", "one more run", "secret")

    result = client.recall("minimize loss")

    request, timeout = calls[0]
    assert result == "- Momentum failed\n- LR improved"
    assert request.full_url.endswith("/banks/one%20more%20run/memories/recall")
    assert request.get_header("Authorization") == "Bearer secret"
    assert json.loads(request.data)["budget"] == "low"
    assert timeout == 5.0


def test_retain_is_asynchronous_and_idempotent(monkeypatch):
    calls = []

    def urlopen(request, timeout):
        calls.append(request)
        return Response(b'{"success":true}')

    monkeypatch.setattr(hindsight.urllib.request, "urlopen", urlopen)
    client = Hindsight("http://localhost:8888", "research")

    client.retain("experiment", "candidate-1", {"decision": "keep"}, "campaign")

    request = calls[0]
    body = json.loads(request.data)
    assert request.full_url.endswith("/banks/research/memories")
    assert body["async"] is True
    assert body["items"][0]["document_id"] == "candidate-1"


def test_hindsight_errors_do_not_expose_response_bodies(monkeypatch):
    def urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "denied", {}, None)

    monkeypatch.setattr(hindsight.urllib.request, "urlopen", urlopen)

    with pytest.raises(HindsightError, match="HTTP 401"):
        Hindsight("https://memory.example", "research", "secret").recall("goal")


def test_hindsight_is_enabled_by_a_bank():
    assert from_environment({}) is None

    client = from_environment({"OMR_HINDSIGHT_BANK": "research"})

    assert client == Hindsight("http://localhost:8888", "research")
