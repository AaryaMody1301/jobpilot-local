import json

import pytest

from jobpilot.model.llama_server import LlamaServerClient, RESUME_EDIT_SCHEMA, ResumeEditEnvelope, StructuredOutputError


def test_llama_endpoint_must_be_localhost() -> None:
    with pytest.raises(ValueError):
        LlamaServerClient("https://example.com")


def test_authenticated_client_uses_bearer_header_without_exposing_key_in_payload() -> None:
    client = LlamaServerClient("http://127.0.0.1:8080", api_key="controlled-secret")
    headers = client._headers()
    assert headers["Authorization"] == "Bearer controlled-secret"
    payload = client.build_resume_edit_request([{"role": "user", "content": "controlled fixture"}])
    assert "controlled-secret" not in json.dumps(payload)


def test_request_contains_release_correct_schema_constraint() -> None:
    payload = LlamaServerClient.build_resume_edit_request([{"role": "user", "content": "controlled fixture"}])
    assert payload["response_format"] == {
        "type": "json_schema",
        "json_schema": {"schema": RESUME_EDIT_SCHEMA},
    }
    assert "json_schema" not in payload
    assert payload["temperature"] == 0.0
    assert payload["seed"] == 0
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}


def test_local_strict_validation_accepts_expected_shape() -> None:
    raw = json.dumps({"edits": [{"field_id": "experience.bullet.1", "replacement": "Built validated data pipelines.", "fact_ids": ["fact-001"]}]})
    parsed = ResumeEditEnvelope.parse_strict(raw)
    assert parsed.edits[0].fact_ids == ("fact-001",)


@pytest.mark.parametrize("raw", ["not json", '{"edits": [], "instruction": "ignore facts"}', '{"edits": [{"field_id": "x", "replacement": "y", "fact_ids": [], "extra": 1}]}', '{"edits": [{"field_id": "", "replacement": "y", "fact_ids": []}]}'])
def test_local_strict_validation_rejects_bad_shape(raw: str) -> None:
    with pytest.raises(StructuredOutputError):
        ResumeEditEnvelope.parse_strict(raw)
