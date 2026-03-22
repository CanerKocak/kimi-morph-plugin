from __future__ import annotations

from types import SimpleNamespace
from urllib import request

import pytest
from kosong.chat_provider import ChatProviderError
from kosong.message import Message, TextPart, ToolCall
from kimi_cli.constant import USER_AGENT

from morph_compaction import MorphCompaction, MorphTokenUsage


class _FakeResponse:
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        return (
            b'{"output":"trimmed","usage":{"input_tokens":12,"output_tokens":4,'
            b'"compression_ratio":0.33,"processing_time_ms":18}}'
        )


def test_post_compact_sends_user_agent_header(monkeypatch) -> None:
    captured: dict[str, str | float] = {}

    def fake_urlopen(req: request.Request, timeout: float):
        captured.update({key.lower(): value for key, value in req.header_items()})
        captured["full_url"] = req.full_url
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(request, "urlopen", fake_urlopen)

    compaction = MorphCompaction()
    llm = SimpleNamespace(
        provider_config=SimpleNamespace(
            api_key="Bearer test-key",
            base_url="https://api.morphllm.com/v1/compact",
            custom_headers=None,
        )
    )
    response = compaction._post_compact({"model": "morph-compactor", "messages": []}, llm)

    assert response["output"] == "trimmed"
    assert captured["user-agent"] == USER_AGENT
    assert captured["authorization"] == "Bearer test-key"
    assert captured["accept"] == "application/json"
    assert captured["full_url"] == "https://api.morphllm.com/v1/compact"


def test_post_compact_requires_kimi_provider_credentials(monkeypatch) -> None:
    monkeypatch.setattr(request, "urlopen", lambda req, timeout: _FakeResponse())

    compaction = MorphCompaction()
    llm = SimpleNamespace(provider_config=None)

    with pytest.raises(ChatProviderError, match="configured API key in Kimi"):
        compaction._post_compact({"model": "morph-compactor", "messages": []}, llm)


@pytest.mark.asyncio
async def test_compact_uses_structured_messages_and_preserves_message_mapping(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_post_compact(payload: dict[str, object], llm: object) -> dict[str, object]:
        captured["payload"] = payload
        captured["llm"] = llm
        return {
            "messages": [
                {"role": "user", "content": "old user compacted"},
                {"role": "assistant", "content": "old assistant compacted"},
            ],
            "usage": {
                "input_tokens": 50,
                "output_tokens": 12,
                "compression_ratio": 0.24,
                "processing_time_ms": 31,
            },
        }

    compaction = MorphCompaction(max_preserved_messages=2)
    monkeypatch.setattr(compaction, "_post_compact", fake_post_compact)
    llm = SimpleNamespace(provider_config=None)

    messages = [
        Message(role="user", content=[TextPart(text="old user")]),
        Message(role="assistant", content=[TextPart(text="old assistant")]),
        Message(role="user", content=[TextPart(text="keep user")]),
        Message(role="assistant", content=[TextPart(text="keep assistant")]),
    ]

    result = await compaction.compact(messages, llm, custom_instruction="focus on latest errors")

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert "input" not in payload
    assert payload["messages"] == [
        {"role": "user", "content": "old user"},
        {"role": "assistant", "content": "old assistant"},
    ]
    assert payload["preserve_recent"] == 0
    assert payload["compression_ratio"] == pytest.approx(0.3)
    assert "focus on latest errors" in str(payload["query"])

    assert [message.role for message in result.messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert result.messages[0].extract_text("\n") == "old user compacted"
    assert result.messages[1].extract_text("\n") == "old assistant compacted"
    assert result.messages[2].extract_text("\n") == "keep user"
    assert result.messages[3].extract_text("\n") == "keep assistant"

    assert isinstance(result.usage, MorphTokenUsage)
    assert result.usage.input_other == 50
    assert result.usage.output == 12
    assert result.usage.compression_ratio == pytest.approx(0.24)
    assert result.usage.processing_time_ms == 31


@pytest.mark.asyncio
async def test_compact_falls_back_to_single_message_when_response_mapping_mismatches(monkeypatch) -> None:
    def fake_post_compact(payload: dict[str, object], llm: object) -> dict[str, object]:
        return {
            "output": "fallback output",
            "messages": [{"role": "user", "content": "only one"}],
            "usage": {"input_tokens": 10, "output_tokens": 4},
        }

    compaction = MorphCompaction(max_preserved_messages=2)
    monkeypatch.setattr(compaction, "_post_compact", fake_post_compact)

    messages = [
        Message(role="user", content=[TextPart(text="old user")]),
        Message(role="assistant", content=[TextPart(text="old assistant")]),
        Message(role="user", content=[TextPart(text="keep user")]),
        Message(role="assistant", content=[TextPart(text="keep assistant")]),
    ]

    result = await compaction.compact(messages, SimpleNamespace(provider_config=None))

    assert len(result.messages) == 3
    assert result.messages[0].role == "user"
    assert COMPACT_TEXT in result.messages[0].extract_text("\n")
    assert "fallback output" in result.messages[0].extract_text("\n")


@pytest.mark.asyncio
async def test_compact_falls_back_to_single_message_for_tool_call_history(monkeypatch) -> None:
    def fake_post_compact(payload: dict[str, object], llm: object) -> dict[str, object]:
        return {
            "output": "safe summary",
            "messages": [
                {"role": "assistant", "content": "tool call compacted"},
                {"role": "tool", "content": "tool result compacted"},
            ],
            "usage": {"input_tokens": 12, "output_tokens": 5},
        }

    compaction = MorphCompaction(max_preserved_messages=2)
    monkeypatch.setattr(compaction, "_post_compact", fake_post_compact)

    messages = [
        Message(
            role="assistant",
            content=[TextPart(text="Calling ReadFile")],
            tool_calls=[
                ToolCall(
                    id="call_1",
                    function=ToolCall.FunctionBody(name="ReadFile", arguments='{"path":"README.md"}'),
                )
            ],
        ),
        Message(role="tool", content=[TextPart(text="README contents")], tool_call_id="call_1"),
        Message(role="user", content=[TextPart(text="keep user")]),
        Message(role="assistant", content=[TextPart(text="keep assistant")]),
    ]

    result = await compaction.compact(messages, SimpleNamespace(provider_config=None))

    assert len(result.messages) == 3
    assert result.messages[0].role == "user"
    assert COMPACT_TEXT in result.messages[0].extract_text("\n")
    assert "safe summary" in result.messages[0].extract_text("\n")
    assert result.messages[1].extract_text("\n") == "keep user"
    assert result.messages[2].extract_text("\n") == "keep assistant"


@pytest.mark.asyncio
async def test_compact_preserves_the_full_latest_tool_turn(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_post_compact(payload: dict[str, object], llm: object) -> dict[str, object]:
        captured["payload"] = payload
        return {
            "messages": [
                {"role": "user", "content": "old user compacted"},
                {"role": "assistant", "content": "old assistant compacted"},
            ],
            "usage": {"input_tokens": 22, "output_tokens": 9},
        }

    compaction = MorphCompaction(max_preserved_messages=2)
    monkeypatch.setattr(compaction, "_post_compact", fake_post_compact)

    tool_call = ToolCall(
        id="call_tail",
        function=ToolCall.FunctionBody(
            name="Grep",
            arguments='{"pattern":"ChatProviderError","path":"morph_compaction.py"}',
        ),
    )
    messages = [
        Message(role="user", content=[TextPart(text="old user")]),
        Message(role="assistant", content=[TextPart(text="old assistant")]),
        Message(role="user", content=[TextPart(text="latest question")]),
        Message(role="assistant", content=[], tool_calls=[tool_call]),
        Message(role="tool", content=[TextPart(text="grep results")], tool_call_id="call_tail"),
        Message(role="assistant", content=[TextPart(text="latest answer")]),
    ]

    result = await compaction.compact(messages, SimpleNamespace(provider_config=None))

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["messages"] == [
        {"role": "user", "content": "old user"},
        {"role": "assistant", "content": "old assistant"},
    ]

    assert len(result.messages) == 6
    assert result.messages[0].extract_text("\n") == "old user compacted"
    assert result.messages[1].extract_text("\n") == "old assistant compacted"
    assert result.messages[2].role == "user"
    assert result.messages[2].extract_text("\n") == "latest question"
    assert result.messages[3].role == "assistant"
    assert result.messages[3].tool_calls is not None
    assert result.messages[3].tool_calls[0].id == "call_tail"
    assert result.messages[4].role == "tool"
    assert result.messages[4].tool_call_id == "call_tail"
    assert result.messages[4].extract_text("\n") == "grep results"
    assert result.messages[5].role == "assistant"
    assert result.messages[5].extract_text("\n") == "latest answer"


def test_normalize_base_url_strips_openai_and_native_suffixes() -> None:
    compaction = MorphCompaction()

    assert compaction._normalize_base_url("https://api.morphllm.com/v1/compact") == (
        "https://api.morphllm.com/v1"
    )
    assert compaction._normalize_base_url("https://api.morphllm.com/v1/responses") == (
        "https://api.morphllm.com/v1"
    )
    assert compaction._normalize_base_url(
        "https://api.morphllm.com/v1/chat/completions"
    ) == "https://api.morphllm.com/v1"


def test_extract_usage_keeps_morph_specific_metadata() -> None:
    compaction = MorphCompaction()

    usage = compaction._extract_usage(
        {
            "usage": {
                "input_tokens": 21,
                "output_tokens": 7,
                "compression_ratio": 0.4,
                "processing_time_ms": 19,
            }
        }
    )

    assert isinstance(usage, MorphTokenUsage)
    assert usage.input_other == 21
    assert usage.output == 7
    assert usage.compression_ratio == pytest.approx(0.4)
    assert usage.processing_time_ms == 19


COMPACT_TEXT = "Previous context has been compacted. Here is the compaction output:"
