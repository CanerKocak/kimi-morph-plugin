from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple
from urllib import error, request

from kosong.chat_provider import ChatProviderError, TokenUsage
from kosong.message import Message, TextPart

from kimi_cli.constant import USER_AGENT
from kimi_cli.soul.compaction import CompactionResult
from kimi_cli.soul.message import system

DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_COMPRESSION_RATIO = 0.3
MORPH_COMPACTOR_MODEL = "morph-compactor"
COMPACTION_PREAMBLE = "Previous context has been compacted. Here is the compaction output:"
_VALID_CHAT_COMPLETION_SUFFIXES = ("/compact", "/responses", "/chat/completions")


class MorphTokenUsage(TokenUsage):
    compression_ratio: float | None = None
    processing_time_ms: int | None = None


class PreparedMorphInput(NamedTuple):
    original_messages: list[Message]
    api_messages: list[dict[str, str]]
    to_preserve: Sequence[Message]


class MorphCompaction:
    def __init__(
        self,
        *,
        compression_ratio: float = DEFAULT_COMPRESSION_RATIO,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_preserved_messages: int = 2,
    ) -> None:
        self._compression_ratio = compression_ratio
        self._timeout_seconds = timeout_seconds
        self._max_preserved_messages = max_preserved_messages

    async def compact(
        self, messages: Sequence[Message], llm: Any, *, custom_instruction: str = ""
    ) -> CompactionResult:
        prepared = self._prepare_messages(messages)
        if prepared is None:
            return CompactionResult(messages=messages, usage=None)
        if not prepared.api_messages:
            return CompactionResult(messages=prepared.to_preserve, usage=None)

        payload = {
            "model": MORPH_COMPACTOR_MODEL,
            "messages": prepared.api_messages,
            "query": self._build_query(custom_instruction),
            "compression_ratio": self._compression_ratio,
            "preserve_recent": 0,
            "compress_system_messages": False,
            "include_line_ranges": True,
            "include_markers": True,
        }
        response = await asyncio.to_thread(self._post_compact, payload, llm)
        output = self._extract_output(response)
        usage = self._extract_usage(response)
        compacted_messages = self._build_compacted_messages(
            prepared.original_messages,
            response,
            fallback_output=output,
        )

        return CompactionResult(messages=[*compacted_messages, *prepared.to_preserve], usage=usage)

    def _prepare_messages(self, messages: Sequence[Message]) -> PreparedMorphInput | None:
        if not messages or self._max_preserved_messages <= 0:
            return None

        history = list(messages)
        preserve_start_index = len(history)
        n_preserved = 0
        for index in range(len(history) - 1, -1, -1):
            if self._counts_toward_preserved_tail(history[index]):
                n_preserved += 1
                if n_preserved == self._max_preserved_messages:
                    preserve_start_index = index
                    break

        if n_preserved < self._max_preserved_messages:
            return None

        to_compact = history[:preserve_start_index]
        to_preserve = history[preserve_start_index:]
        if not to_compact:
            return None

        original_messages: list[Message] = []
        api_messages: list[dict[str, str]] = []
        for message in to_compact:
            text = self._extract_text_content(message)
            if text is None:
                continue
            original_messages.append(message)
            api_messages.append({"role": message.role, "content": text})

        return PreparedMorphInput(
            original_messages=original_messages,
            api_messages=api_messages,
            to_preserve=to_preserve,
        )

    def _counts_toward_preserved_tail(self, message: Message) -> bool:
        if message.role == "user":
            return True
        if message.role == "assistant" and not message.tool_calls:
            return True
        return False

    def _extract_text_content(self, message: Message) -> str | None:
        parts = [part.text for part in message.content if isinstance(part, TextPart) and part.text]
        if not parts:
            return None
        return "\n".join(parts)

    def _build_query(self, custom_instruction: str) -> str:
        query = (
            "Keep only the context still needed to continue the coding task accurately. "
            "Preserve exact filenames, commands, errors, constraints, decisions, and open work. "
            "Drop repetition and stale context."
        )
        if custom_instruction:
            query += f" Prioritize this user instruction: {custom_instruction}"
        return query

    def _post_compact(self, payload: dict[str, Any], llm: Any) -> dict[str, Any]:
        provider = getattr(llm, "provider_config", None)
        api_key = self._resolve_api_key(provider)
        if not api_key:
            raise ChatProviderError("Morph compaction requires a configured API key in Kimi.")

        base_url = self._resolve_base_url(provider)
        if not base_url:
            raise ChatProviderError("Morph compaction requires a configured base URL in Kimi.")

        url = f"{self._normalize_base_url(base_url)}/compact"
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._build_headers(provider, api_key),
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as resp:
                body = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ChatProviderError(
                f"Morph compact request failed with status {exc.code}: {body}"
            ) from exc
        except error.URLError as exc:
            raise ChatProviderError(f"Morph compact request failed: {exc.reason}") from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ChatProviderError("Morph compact response was not valid JSON.") from exc

        if not isinstance(data, dict):
            raise ChatProviderError("Morph compact response had unexpected shape.")
        return data

    def _resolve_api_key(self, provider: Any) -> str | None:
        api_key = getattr(provider, "api_key", None)
        if api_key is None:
            return None
        if hasattr(api_key, "get_secret_value"):
            value = api_key.get_secret_value()
            return value or None
        if isinstance(api_key, str) and api_key:
            return api_key
        return None

    def _resolve_base_url(self, provider: Any) -> str | None:
        base_url = getattr(provider, "base_url", None)
        if isinstance(base_url, str) and base_url:
            return base_url
        return None

    def _build_headers(self, provider: Any, api_key: str) -> dict[str, str]:
        normalized_api_key = self._normalize_api_key(api_key)
        headers = {
            "Authorization": f"Bearer {normalized_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        custom_headers = getattr(provider, "custom_headers", None)
        if isinstance(custom_headers, Mapping):
            for key, value in custom_headers.items():
                if isinstance(key, str) and isinstance(value, str):
                    headers[key] = value
        return headers

    def _normalize_api_key(self, api_key: str) -> str:
        normalized = api_key.strip()
        if normalized.lower().startswith("bearer "):
            return normalized[7:].strip()
        return normalized

    def _normalize_base_url(self, base_url: str) -> str:
        normalized = base_url.strip().rstrip("/")
        for suffix in _VALID_CHAT_COMPLETION_SUFFIXES:
            if normalized.endswith(suffix):
                return normalized[: -len(suffix)]
        return normalized

    def _build_compacted_messages(
        self,
        original_messages: Sequence[Message],
        response: dict[str, Any],
        *,
        fallback_output: str,
    ) -> list[Message]:
        if self._requires_fallback_compaction(original_messages):
            return [self._build_fallback_message(fallback_output)]

        response_messages = response.get("messages")
        if isinstance(response_messages, list) and len(response_messages) == len(original_messages):
            compacted_messages: list[Message] = []
            for original, compacted in zip(original_messages, response_messages, strict=True):
                if not isinstance(compacted, dict):
                    return [self._build_fallback_message(fallback_output)]

                content = compacted.get("content")
                if not isinstance(content, str) or not content:
                    return [self._build_fallback_message(fallback_output)]

                role = compacted.get("role")
                if not isinstance(role, str) or not role:
                    role = original.role

                compacted_messages.append(Message(role=role, content=[TextPart(text=content)]))
            return compacted_messages

        return [self._build_fallback_message(fallback_output)]

    def _requires_fallback_compaction(self, original_messages: Sequence[Message]) -> bool:
        for message in original_messages:
            if message.role == "tool" or message.tool_calls or message.tool_call_id:
                return True
            if any(not isinstance(part, TextPart) for part in message.content):
                return True
        return False

    def _build_fallback_message(self, output: str) -> Message:
        content = [system(COMPACTION_PREAMBLE), TextPart(text=output)]
        return Message(role="user", content=content)

    def _extract_output(self, response: dict[str, Any]) -> str:
        output = response.get("output")
        if isinstance(output, str) and output.strip():
            return output

        messages = response.get("messages")
        if isinstance(messages, list):
            parts: list[str] = []
            for message in messages:
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content:
                        parts.append(content)
            if parts:
                return "\n\n".join(parts)

        raise ChatProviderError("Morph compact response did not contain output text.")

    def _extract_usage(self, response: dict[str, Any]) -> MorphTokenUsage | None:
        usage = response.get("usage")
        if not isinstance(usage, dict):
            return None

        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
            return None

        compression_ratio = usage.get("compression_ratio")
        if not isinstance(compression_ratio, (int, float)):
            compression_ratio = None

        processing_time_ms = usage.get("processing_time_ms")
        if not isinstance(processing_time_ms, int):
            processing_time_ms = None

        return MorphTokenUsage(
            input_other=input_tokens,
            output=output_tokens,
            compression_ratio=float(compression_ratio) if compression_ratio is not None else None,
            processing_time_ms=processing_time_ms,
        )
