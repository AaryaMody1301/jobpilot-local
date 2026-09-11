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


def test_request_uses_llama_cpp_native_schema_constraint_not_openai_nested_wrapper() -> None:
    payload = LlamaServerClient.build_resume_edit_request([{"role": "user", "content": "controlled fixture"}])
    assert payload["response_format"] == {
        "type": "json_schema",
        "schema": RESUME_EDIT_SCHEMA,
    }
    assert "json_schema" not in payload["response_format"]
    assert "json_schema" not in payload
    assert payload["temperature"] == 0.0
    assert payload["seed"] == 0
    assert payload["reasoning_effort"] == "none"
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}


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
