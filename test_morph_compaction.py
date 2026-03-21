from __future__ import annotations

from types import SimpleNamespace
from urllib import request

from kimi_cli.constant import USER_AGENT

from morph_compaction import MorphCompaction


class _FakeResponse:
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        return b'{"output":"trimmed","usage":{"input_tokens":12,"output_tokens":4}}'


def test_post_compact_sends_user_agent_header(monkeypatch) -> None:
    captured: dict[str, str | float] = {}

    def fake_urlopen(req: request.Request, timeout: float):
        captured.update({key.lower(): value for key, value in req.header_items()})
        captured["full_url"] = req.full_url
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setenv("MORPH_API_KEY", "Bearer test-key")
    monkeypatch.setenv("MORPH_API_URL", "https://api.morphllm.com/v1/compact")
    monkeypatch.setattr(request, "urlopen", fake_urlopen)

    compaction = MorphCompaction()
    llm = SimpleNamespace(provider_config=None)
    response = compaction._post_compact({"model": "morph-compactor", "input": "hello"}, llm)

    assert response["output"] == "trimmed"
    assert captured["user-agent"] == USER_AGENT
    assert captured["authorization"] == "Bearer test-key"
    assert captured["accept"] == "application/json"
    assert captured["full_url"] == "https://api.morphllm.com/v1/compact"