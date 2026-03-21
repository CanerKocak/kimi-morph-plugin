from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping, Sequence
from typing import Any
from urllib import error, request

from kosong.chat_provider import ChatProviderError, TokenUsage
from kosong.message import Message, TextPart

from kimi_cli.constant import USER_AGENT
from kimi_cli.soul.compaction import CompactionResult, SimpleCompaction
from kimi_cli.soul.message import system

DEFAULT_MORPH_API_URL = "https://api.morphllm.com/v1"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_COMPRESSION_RATIO = 0.5
MORPH_COMPACTOR_MODEL = "morph-compactor"
COMPACTION_PREAMBLE = "Previous context has been compacted. Here is the compaction output:"


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
        self._base = SimpleCompaction(max_preserved_messages=max_preserved_messages)

    async def compact(
        self, messages: Sequence[Message], llm: Any, *, custom_instruction: str = ""
    ) -> CompactionResult:
        compact_message, to_preserve = self._base.prepare(
            messages,
            custom_instruction=custom_instruction,
        )
        if compact_message is None:
            return CompactionResult(messages=to_preserve, usage=None)

        payload = {
            "model": MORPH_COMPACTOR_MODEL,
            "input": compact_message.extract_text("\n"),
            "query": self._build_query(custom_instruction),
            "compression_ratio": self._compression_ratio,
            "compress_system_messages": False,
            "include_line_ranges": True,
            "include_markers": True,
        }
        response = await asyncio.to_thread(self._post_compact, payload, llm)
        output = self._extract_output(response)
        usage = self._extract_usage(response)

        content = [system(COMPACTION_PREAMBLE), TextPart(text=output)]
        compacted_messages = [Message(role="user", content=content), *to_preserve]
        return CompactionResult(messages=compacted_messages, usage=usage)

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
        api_key = self._resolve_api_key(provider) or os.getenv("MORPH_API_KEY")
        if not api_key:
            raise ChatProviderError(
                "Morph compaction requires a configured API key in Kimi or MORPH_API_KEY."
            )

        base_url = (
            self._resolve_base_url(provider)
            or os.getenv("MORPH_API_URL")
            or DEFAULT_MORPH_API_URL
        )
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
        if normalized.endswith("/compact"):
            return normalized[: -len("/compact")]
        return normalized

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

    def _extract_usage(self, response: dict[str, Any]) -> TokenUsage | None:
        usage = response.get("usage")
        if not isinstance(usage, dict):
            return None

        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
            return None

        return TokenUsage(input_other=input_tokens, output=output_tokens)
