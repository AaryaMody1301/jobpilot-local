from pathlib import Path

import pytest

from jobpilot.resume.documents import DocumentWorkspace
from jobpilot.resume.store import ResumeStore
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import Database

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def _workspace(tmp_path: Path):
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    paths.create_all_roots()
    db = Database(paths.database_file, MIGRATIONS)
    db.apply_migrations()
    store = ResumeStore(db, paths.root)
    return paths, db, store, DocumentWorkspace(paths, store)


def _resume(path: Path, text: str = "Built verified pipelines.") -> Path:
    path.write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\section{Experience}\n"
        "\\begin{itemize}\n"
        f"\\item {text}\n"
        "\\end{itemize}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    return path


def test_master_import_is_immutable_and_deduplicated(tmp_path: Path) -> None:
    paths, db, store, workspace = _workspace(tmp_path)
    try:
        source = _resume(tmp_path / "resume.tex")
        first = workspace.import_master(source)
        master = store.get_active_master()
        assert master is not None
        stored = store.document_path(master)
        original_bytes = stored.read_bytes()
        source.write_text("outside mutation", encoding="utf-8")
        assert stored.read_bytes() == original_bytes
        duplicate_source = tmp_path / "same.tex"
        duplicate_source.write_bytes(original_bytes)
        second = workspace.import_master(duplicate_source)
        assert second["document_id"] == first["document_id"]
        assert second["deduplicated"] is True
        assert workspace.verify_active_master() == "verified"
        assert str(stored).startswith(str(paths.master_documents))
    finally:
        db.close()


def test_changed_master_creates_new_version_without_deleting_old(tmp_path: Path) -> None:
    _, db, store, workspace = _workspace(tmp_path)
    try:
        source = _resume(tmp_path / "resume.tex", "First statement.")
        first = workspace.import_master(source)
        _resume(source, "Second statement.")
        second = workspace.import_master(source)
        assert first["document_id"] != second["document_id"]
        rows = store.list_documents("master_resume")
        assert len(rows) == 2
        assert sum(int(row["active"]) for row in rows) == 1
        assert store.get_active_master()["id"] == second["document_id"]
    finally:
        db.close()


def test_fact_corrections_keep_stable_id_and_history(tmp_path: Path) -> None:
    _, db, store, workspace = _workspace(tmp_path)
    try:
        source = _resume(tmp_path / "resume.tex")
        workspace.import_master(source)
        fact = store.list_facts()[0]
        first_revision = store.fact_bank_revision()
        store.set_fact_status(fact["id"], "approved")
        store.revise_fact(fact["id"], value="Built verified local pipelines.", category="experience_bullet")
        current = store.list_facts()[0]
        assert current["id"] == fact["id"]
        assert current["current_version"] == 2
        assert current["current_status"] == "candidate"
        versions = store.fact_versions(fact["id"])
        assert [row["version"] for row in versions] == [1, 2]
        assert versions[0]["status"] == "approved"
        assert versions[1]["source_ref"]["source_sha256"] == store.get_active_master()["sha256"]
        assert store.fact_bank_revision() >= first_revision + 2
    finally:
        db.close()


def test_managed_source_tampering_is_detected(tmp_path: Path) -> None:
    _, db, store, workspace = _workspace(tmp_path)
    try:
        workspace.import_master(_resume(tmp_path / "resume.tex"))
        master = store.get_active_master()
        stored = store.document_path(master)
        stored.write_text("tampered", encoding="utf-8")
        assert workspace.verify_active_master() == "mismatch"
        assert store.get_active_master()["integrity_status"] == "mismatch"
    finally:
        db.close()


def test_supporting_registry_accepts_supported_files_and_rejects_executable(tmp_path: Path) -> None:
    _, db, store, workspace = _workspace(tmp_path)
    try:
        evidence = tmp_path / "evidence.txt"
        evidence.write_text("evidence", encoding="utf-8")
        result = workspace.import_supporting(evidence)
        assert result["deduplicated"] is False
        assert store.list_documents("supporting")[0]["id"] == result["document_id"]
        bad = tmp_path / "payload.exe"
        bad.write_bytes(b"not allowed")
        with pytest.raises(ValueError):
            workspace.import_supporting(bad)
    finally:
        db.close()


def test_template_confirmation_requires_editable_region_and_change_invalidates_confirmation(tmp_path: Path) -> None:
    _, db, store, workspace = _workspace(tmp_path)
    try:
        workspace.import_master(_resume(tmp_path / "resume.tex"))
        master = store.get_active_master()
        region = store.list_template_regions(master["id"])[0]
        with pytest.raises(ValueError):
            store.confirm_template_map(master["id"])
        store.set_region_editable(region["id"], True)
        store.confirm_template_map(master["id"])
        assert store.template_map_status(master["id"]) == "confirmed"
        store.set_region_editable(region["id"], False)
        assert store.template_map_status(master["id"]) == "candidate"
    finally:
        db.close()


def test_candidate_fact_category_is_conservative_by_section(tmp_path: Path) -> None:
    _, db, store, workspace = _workspace(tmp_path)
    try:
        source = tmp_path / "resume.tex"
        source.write_text(
            "\\documentclass{article}\n\\begin{document}\n"
            "\\section{Education}\n\\begin{itemize}\n\\item Bachelor of Example Science.\n\\end{itemize}\n"
            "\\section{Skills}\n\\begin{itemize}\n\\item SQL and Python.\n\\end{itemize}\n"
            "\\section{Summary}\n\\begin{itemize}\n\\item Evidence-backed analyst.\n\\end{itemize}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        workspace.import_master(source)
        categories = [fact["current_category"] for fact in store.list_facts()]
        assert categories == ["qualification", "skill", "other"]
    finally:
        db.close()
