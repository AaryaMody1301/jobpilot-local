from __future__ import annotations

import pytest

from jobpilot.model.llama_server import StructuredOutputError
from jobpilot.resume.tailoring import TailoringPlan, validate_tailoring_plan


def _fact() -> dict[str, object]:
    return {
        "id": "fact-sql",
        "value_text": "Built SQL reports",
        "current_category": "achievement",
        "current_status": "approved",
        "source_ref": {"kind": "latex_region", "region_id": "field-1"},
    }


def _validate(replacement: str) -> None:
    plan = TailoringPlan.from_value(
        {
            "keyword_mappings": [{"keyword": "SQL", "fact_ids": ["fact-sql"]}],
            "edits": [
                {
                    "field_id": "field-1",
                    "replacement": replacement,
                    "fact_ids": ["fact-sql"],
                    "keywords": ["SQL"],
                }
            ],
        }
    )
    validate_tailoring_plan(
        plan,
        jd_text="SQL is required.",
        editable_regions={"field-1": {"id": "field-1", "editable": 1, "display_text": "Built SQL reports"}},
        approved_facts={"fact-sql": _fact()},
    )


def test_rejects_repeated_supported_term_keyword_stuffing() -> None:
    with pytest.raises(StructuredOutputError, match="anti-keyword-stuffing"):
        _validate("Built SQL SQL SQL SQL reports")


def test_rejects_zero_width_hidden_text() -> None:
    with pytest.raises(StructuredOutputError, match="hidden Unicode"):
        _validate("Built SQL\u200b reports")


def test_allows_natural_supported_repetition_within_evidence_bound() -> None:
    _validate("Built SQL reports")
