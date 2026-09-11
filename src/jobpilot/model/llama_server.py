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


def validate_json_schema_subset(value: Any, schema: Mapping[str, Any], path: str = "$") -> None:
    """Validate the deliberately small JSON-schema subset used by JobPilot locally.

    llama.cpp constraints improve generation reliability, but this validator is an
    independent application-side gate. Unsupported schema keywords fail closed so a
    future schema change cannot silently become less strict.
    """

    supported = {"type", "additionalProperties", "properties", "required", "items", "enum", "maxLength", "minLength"}
    unknown = set(schema) - supported
    if unknown:
        raise StructuredOutputError(f"unsupported local schema keyword(s) at {path}: {sorted(unknown)}")

    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            raise StructuredOutputError(f"{path} must be an object")
        properties = schema.get("properties", {})
        if not isinstance(properties, Mapping):
            raise StructuredOutputError(f"{path} schema properties must be an object")
        required = schema.get("required", [])
        if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
            raise StructuredOutputError(f"{path} schema required must be a string array")
        missing = [name for name in required if name not in value]
        if missing:
            raise StructuredOutputError(f"{path} is missing required field(s): {missing}")
        if schema.get("additionalProperties") is False:
            extras = set(value) - set(properties)
            if extras:
                raise StructuredOutputError(f"{path} contains unexpected field(s): {sorted(extras)}")
        for name, child_schema in properties.items():
            if name in value:
                if not isinstance(child_schema, Mapping):
                    raise StructuredOutputError(f"schema for {path}.{name} must be an object")
                validate_json_schema_subset(value[name], child_schema, f"{path}.{name}")
    elif expected_type == "array":
        if not isinstance(value, list):
            raise StructuredOutputError(f"{path} must be an array")
        item_schema = schema.get("items")
        if item_schema is not None:
            if not isinstance(item_schema, Mapping):
                raise StructuredOutputError(f"{path} schema items must be an object")
            for index, item in enumerate(value):
                validate_json_schema_subset(item, item_schema, f"{path}[{index}]")
    elif expected_type == "string":
        if not isinstance(value, str):
            raise StructuredOutputError(f"{path} must be a string")
        min_length = schema.get("minLength")
        max_length = schema.get("maxLength")
        if min_length is not None and len(value) < int(min_length):
            raise StructuredOutputError(f"{path} is shorter than minLength")
        if max_length is not None and len(value) > int(max_length):
            raise StructuredOutputError(f"{path} exceeds maxLength")
    elif expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise StructuredOutputError(f"{path} must be an integer")
    elif expected_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise StructuredOutputError(f"{path} must be a number")
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            raise StructuredOutputError(f"{path} must be a boolean")
    elif expected_type is not None:
        raise StructuredOutputError(f"unsupported local schema type at {path}: {expected_type!r}")

    enum = schema.get("enum")
    if enum is not None:
        if not isinstance(enum, list):
            raise StructuredOutputError(f"{path} schema enum must be an array")
        if value not in enum:
            raise StructuredOutputError(f"{path} is not an allowed enum value")


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
        validate_json_schema_subset(value, RESUME_EDIT_SCHEMA)
        edits: list[ResumeEdit] = []
        for index, item in enumerate(value["edits"]):
            field_id = item["field_id"]
            replacement = item["replacement"]
            fact_ids = item["fact_ids"]
            if not field_id:
                raise StructuredOutputError(f"edit {index} field_id must be non-empty string")
            if any(not fact_id for fact_id in fact_ids):
                raise StructuredOutputError(f"edit {index} fact_ids must be non-empty strings")
            edits.append(ResumeEdit(field_id, replacement, tuple(fact_ids)))
        return cls(tuple(edits))


@dataclass(frozen=True, slots=True)
class StructuredJsonResponse:
    value: dict[str, Any]
    timings: dict[str, Any]
    usage: dict[str, Any]


class LlamaServerClient:
    """Small authenticated localhost-only client; server constraints and local validation are separate gates."""

    def __init__(self, base_url: str = "http://127.0.0.1:8080", *, api_key: str | None = None) -> None:
        if not (base_url.startswith("http://127.0.0.1:") or base_url.startswith("http://localhost:")):
            raise ValueError("llama.cpp endpoint must be localhost")
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key

    @staticmethod
    def build_structured_request(
        messages: Sequence[Mapping[str, str]],
        schema: Mapping[str, Any],
        *,
        temperature: float = 0.0,
        max_tokens: int = 256,
    ) -> dict[str, Any]:
        # b10809's server implementation parses type=json_schema from
        # response_format.json_schema.schema, even though the same tag's README shows
        # a direct response_format.schema example. Pin to the executable's parser
        # contract and validate the response independently below.
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
                "json_schema": {
                    "name": "jobpilot_response",
                    "strict": True,
                    "schema": dict(schema),
                },
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

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

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
            headers=self._headers(),
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
        validate_json_schema_subset(value, schema)
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
