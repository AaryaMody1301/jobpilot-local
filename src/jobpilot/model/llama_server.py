from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class StructuredOutputError(ValueError):
    pass


RESUME_EDIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "edits": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "field_id": {"type": "string"},
                    "replacement": {"type": "string"},
                    "fact_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["field_id", "replacement", "fact_ids"],
            },
        }
    },
    "required": ["edits"],
}


@dataclass(frozen=True, slots=True)
class ResumeEdit:
    field_id: str
    replacement: str
    fact_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResumeEditEnvelope:
    edits: tuple[ResumeEdit, ...]

    @classmethod
    def parse_strict(cls, raw: str) -> "ResumeEditEnvelope":
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StructuredOutputError(f"model output is not JSON: {exc}") from exc
        if not isinstance(value, dict) or set(value) != {"edits"}:
            raise StructuredOutputError("expected object containing only 'edits'")
        edits_value = value["edits"]
        if not isinstance(edits_value, list):
            raise StructuredOutputError("'edits' must be an array")
        edits: list[ResumeEdit] = []
        for index, item in enumerate(edits_value):
            if not isinstance(item, dict) or set(item) != {"field_id", "replacement", "fact_ids"}:
                raise StructuredOutputError(f"edit {index} has unexpected fields")
            field_id = item["field_id"]
            replacement = item["replacement"]
            fact_ids = item["fact_ids"]
            if not isinstance(field_id, str) or not field_id:
                raise StructuredOutputError(f"edit {index} field_id must be non-empty string")
            if not isinstance(replacement, str):
                raise StructuredOutputError(f"edit {index} replacement must be string")
            if not isinstance(fact_ids, list) or any(not isinstance(v, str) or not v for v in fact_ids):
                raise StructuredOutputError(f"edit {index} fact_ids must be non-empty strings")
            edits.append(ResumeEdit(field_id, replacement, tuple(fact_ids)))
        return cls(tuple(edits))


@dataclass(frozen=True, slots=True)
class StructuredJsonResponse:
    value: dict[str, Any]
    timings: dict[str, Any]
    usage: dict[str, Any]


class LlamaServerClient:
    """Small localhost-only client; structural and factual validation remains local."""

    def __init__(self, base_url: str = "http://127.0.0.1:8080") -> None:
        if not (base_url.startswith("http://127.0.0.1:") or base_url.startswith("http://localhost:")):
            raise ValueError("llama.cpp endpoint must be localhost")
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def build_structured_request(
        messages: Sequence[Mapping[str, str]],
        schema: Mapping[str, Any],
        *,
        temperature: float = 0.0,
        max_tokens: int = 256,
    ) -> dict[str, Any]:
        return {
            "messages": [dict(message) for message in messages],
            "temperature": temperature,
            "seed": 0,
            "max_tokens": int(max_tokens),
            "cache_prompt": False,
            "reasoning_effort": "none",
            "chat_template_kwargs": {"enable_thinking": False},
            "response_format": {
                "type": "json_schema",
                "schema": dict(schema),
            },
        }

    @classmethod
    def build_resume_edit_request(
        cls,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        return cls.build_structured_request(messages, RESUME_EDIT_SCHEMA, temperature=temperature)

    def request_structured(
        self,
        messages: Sequence[Mapping[str, str]],
        schema: Mapping[str, Any],
        *,
        timeout_seconds: int = 120,
        max_tokens: int = 256,
    ) -> StructuredJsonResponse:
        payload = self.build_structured_request(messages, schema, max_tokens=max_tokens)
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        try:
            raw_content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise StructuredOutputError("unexpected llama.cpp response shape") from exc
        if not isinstance(raw_content, str):
            raise StructuredOutputError("llama.cpp content is not text")
        try:
            value = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise StructuredOutputError(f"llama.cpp content is not JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise StructuredOutputError("llama.cpp structured response must be an object")
        timings = body.get("timings") if isinstance(body.get("timings"), dict) else {}
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        return StructuredJsonResponse(value=value, timings=dict(timings), usage=dict(usage))

    def request_resume_edits(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        timeout_seconds: int = 120,
    ) -> ResumeEditEnvelope:
        response = self.request_structured(messages, RESUME_EDIT_SCHEMA, timeout_seconds=timeout_seconds)
        return ResumeEditEnvelope.parse_strict(json.dumps(response.value, separators=(",", ":")))
