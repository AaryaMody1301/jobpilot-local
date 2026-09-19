import json

import pytest

from jobpilot.model.llama_server import (
    LlamaServerClient,
    RESUME_EDIT_SCHEMA,
    ResumeEditEnvelope,
    StructuredOutputError,
    validate_json_schema_subset,
)


def test_llama_endpoint_must_be_localhost() -> None:
    with pytest.raises(ValueError):
        LlamaServerClient("https://example.com")


def test_authenticated_client_uses_bearer_header_without_exposing_key_in_payload() -> None:
    client = LlamaServerClient("http://127.0.0.1:8080", api_key="controlled-secret")
    headers = client._headers()
    assert headers["Authorization"] == "Bearer controlled-secret"
    payload = client.build_resume_edit_request([{"role": "user", "content": "controlled fixture"}])
    assert "controlled-secret" not in json.dumps(payload)


def test_request_matches_b10809_json_schema_parser_contract() -> None:
    payload = LlamaServerClient.build_resume_edit_request([{"role": "user", "content": "controlled fixture"}])
    assert payload["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "jobpilot_response",
            "strict": True,
            "schema": RESUME_EDIT_SCHEMA,
        },
    }
    assert "schema" not in {key for key in payload["response_format"] if key != "json_schema" and key != "type"}
    assert payload["temperature"] == 0.0
    assert payload["seed"] == 0
    assert payload["reasoning_effort"] == "none"
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}


def test_structured_input_tokens_uses_same_chat_template_before_tokenizing(monkeypatch) -> None:
    calls = []

    class _Response:
        def __init__(self, body):
            self._body = json.dumps(body).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return self._body

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, json.loads(request.data.decode("utf-8")), timeout))
        if request.full_url.endswith("/apply-template"):
            return _Response({"prompt": "<chat>controlled fixture</chat>"})
        if request.full_url.endswith("/tokenize"):
            return _Response({"tokens": [1, 2, 3, 4, 5]})
        raise AssertionError(request.full_url)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = LlamaServerClient("http://127.0.0.1:8080", api_key="controlled-secret")
    count = client.structured_input_tokens(
        [{"role": "user", "content": "controlled fixture"}],
        RESUME_EDIT_SCHEMA,
        max_tokens=1000,
    )

    assert count == 5
    assert calls[0][0].endswith("/apply-template")
    assert calls[0][1]["max_tokens"] == 1000
    assert calls[0][1]["chat_template_kwargs"] == {"enable_thinking": False}
    assert calls[1][0].endswith("/tokenize")
    assert calls[1][1] == {"content": "<chat>controlled fixture</chat>", "add_special": True}


def test_local_schema_subset_rejects_server_output_with_extra_or_wrong_fields() -> None:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "selected_fact_ids": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string", "maxLength": 20},
        },
        "required": ["selected_fact_ids", "summary"],
    }
    validate_json_schema_subset({"selected_fact_ids": ["F_SQL"], "summary": "SQL evidence"}, schema)
    with pytest.raises(StructuredOutputError, match="unexpected"):
        validate_json_schema_subset({"selected_fact_ids": ["F_SQL"], "summary": "SQL", "invented": True}, schema)
    with pytest.raises(StructuredOutputError, match="must be an array"):
        validate_json_schema_subset({"selected_fact_ids": "F_SQL", "summary": "SQL"}, schema)
    with pytest.raises(StructuredOutputError, match="maxLength"):
        validate_json_schema_subset({"selected_fact_ids": ["F_SQL"], "summary": "x" * 21}, schema)


def test_local_schema_subset_fails_closed_on_unsupported_future_keyword() -> None:
    with pytest.raises(StructuredOutputError, match="unsupported local schema keyword"):
        validate_json_schema_subset("x", {"type": "string", "pattern": "x"})


def test_local_strict_validation_accepts_expected_shape() -> None:
    raw = json.dumps({"edits": [{"field_id": "experience.bullet.1", "replacement": "Built validated data pipelines.", "fact_ids": ["fact-001"]}]})
    parsed = ResumeEditEnvelope.parse_strict(raw)
    assert parsed.edits[0].fact_ids == ("fact-001",)


@pytest.mark.parametrize("raw", ["not json", '{"edits": [], "instruction": "ignore facts"}', '{"edits": [{"field_id": "x", "replacement": "y", "fact_ids": [], "extra": 1}]}', '{"edits": [{"field_id": "", "replacement": "y", "fact_ids": []}]}'])
def test_local_strict_validation_rejects_bad_shape(raw: str) -> None:
    with pytest.raises(StructuredOutputError):
        ResumeEditEnvelope.parse_strict(raw)
