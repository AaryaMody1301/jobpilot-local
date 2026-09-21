from __future__ import annotations

import hashlib
from pathlib import Path

from jobpilot.app.controller import ApplicationController
from jobpilot.resume.documents import DocumentWorkspace
from jobpilot.resume.facts import extract_protected_facts
from jobpilot.resume.store import ResumeStore
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import Database

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"
FIXTURE = ROOT / "tests" / "fixtures" / "phase2_template_shape.tex"


def test_protected_extractor_covers_non_bullet_facts_without_layout_noise() -> None:
    source = FIXTURE.read_text(encoding="utf-8")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    facts = extract_protected_facts(source, digest)
    values = [fact.value for fact in facts]

    assert "Data Analyst" in values
    assert "Feb 2026 -- Present" in values
    assert "Example Manufacturing, Inc." in values
    assert "Example City, India" in values
    assert any(value.startswith("Programming & Querying:") for value in values)
    assert any("Bachelor of Science in Information Technology" in value for value in values)
    assert any("GPA: 8.50 / 10" in value for value in values)
    assert "Python, dbt, DuckDB, local AI" in values
    assert any(value.startswith("English -- C2") for value in values)
    assert not any("3pt" in value for value in values)

    role_facts = [fact for fact in facts if fact.extractor_kind.startswith("role_")]
    assert len(role_facts) == 8
    assert {fact.category for fact in role_facts} == {"title", "date", "employer", "location"}
    assert all(fact.source_ref(digest)["source_sha256"] == digest for fact in facts)


def test_document_import_adds_protected_and_bullet_facts(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    paths.create_all_roots()
    database = Database(paths.database_file, MIGRATIONS)
    database.apply_migrations()
    store = ResumeStore(database, paths.root)
    workspace = DocumentWorkspace(paths, store)
    try:
        result = workspace.import_master(FIXTURE)
        facts = store.list_facts()
        categories = {fact["current_category"] for fact in facts}
        assert result["candidate_facts_created"] == len(facts)
        assert len(facts) > 10
        assert {"experience_bullet", "title", "date", "employer", "location", "skill", "qualification"} <= categories
        assert all(fact["current_status"] == "candidate" for fact in facts)
        assert all(fact["source_ref"]["source_sha256"] == store.get_active_master()["sha256"] for fact in facts)
    finally:
        database.close()


def test_current_fact_gate_excludes_inactive_master_versions(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    controller = ApplicationController(paths, MIGRATIONS, sample_item_seconds=0.01)
    try:
        first = tmp_path / "first.tex"
        first.write_text(
            "\\documentclass{article}\n\\begin{document}\n\\section{Experience}\n"
            "\\begin{itemize}\n\\item First source fact.\n\\end{itemize}\n\\end{document}\n",
            encoding="utf-8",
        )
        controller.import_master_resume(first)
        first_state = controller.snapshot()["resume"]
        first_master_id = str(first_state["master"]["id"])
        assert first_state["fact_counts"]["candidate"] == 1

        second = tmp_path / "second.tex"
        second.write_text(
            "\\documentclass{article}\n\\begin{document}\n\\section{Experience}\n"
            "\\begin{itemize}\n\\item Second source fact.\n\\end{itemize}\n\\end{document}\n",
            encoding="utf-8",
        )
        second_state = controller.import_master_resume(second)["resume"]
        second_master_id = str(second_state["master"]["id"])
        assert second_master_id != first_master_id
        assert second_state["fact_counts"]["candidate"] == 1
        assert {str(fact["source_document_id"]) for fact in second_state["facts"]} == {second_master_id}
        assert len(controller.resume_store.list_facts()) == 2
    finally:
        controller.close()
