from __future__ import annotations

import hashlib
import mimetypes
import shutil
from pathlib import Path
from typing import Any

from jobpilot.resume.store import ResumeStore
from jobpilot.resume.template_map import map_editable_regions, source_metrics
from jobpilot.runtime.paths import ManagedPaths

MASTER_MAX_BYTES = 10 * 1024 * 1024
SUPPORTING_MAX_BYTES = 40 * 1024 * 1024
SUPPORTING_SUFFIXES = {".pdf", ".txt", ".md", ".tex"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class DocumentWorkspace:
    def __init__(self, paths: ManagedPaths, store: ResumeStore) -> None:
        self.paths = paths
        self.store = store

    @staticmethod
    def _validate_source(source: Path, *, master: bool) -> tuple[int, str]:
        if not source.is_file():
            raise ValueError("selected document is not a file")
        suffix = source.suffix.lower()
        if master and suffix != ".tex":
            raise ValueError("the master resume must be a .tex file")
        if not master and suffix not in SUPPORTING_SUFFIXES:
            raise ValueError("supporting documents must be .pdf, .txt, .md, or .tex")
        size = source.stat().st_size
        limit = MASTER_MAX_BYTES if master else SUPPORTING_MAX_BYTES
        if size <= 0 or size > limit:
            raise ValueError(f"document size must be between 1 byte and {limit} bytes")
        return size, suffix

    def import_master(self, source: Path) -> dict[str, Any]:
        source = source.resolve(strict=True)
        byte_size, _ = self._validate_source(source, master=True)
        digest = sha256_file(source)
        existing = self.store.find_document_by_digest("master_resume", digest)
        if existing is not None:
            stored = self.store.document_path(existing)
            if not stored.is_file() or sha256_file(stored) != digest:
                self.store.set_integrity(str(existing["id"]), "missing" if not stored.exists() else "mismatch")
                raise RuntimeError("the previously imported immutable master no longer matches its recorded hash")
            self.store.activate_existing_master(str(existing["id"]))
            created = self._initialize_master(str(existing["id"]), stored, digest)
            return {"document_id": existing["id"], "deduplicated": True, "candidate_facts_created": created}

        document_id = f"resume-{digest[:16]}"
        target_dir = self.paths.master_documents / document_id
        target = target_dir / "source.tex"
        target_dir.mkdir(parents=True, exist_ok=False)
        try:
            with source.open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            if sha256_file(target) != digest:
                raise RuntimeError("immutable resume copy failed hash verification")
            try:
                source_text = target.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ValueError("the .tex resume must be UTF-8 text") from exc
            media_type = mimetypes.guess_type(source.name)[0] or "application/x-tex"
            self.store.register_document(
                document_id=document_id,
                kind="master_resume",
                original_name=source.name,
                stored_path=target,
                sha256=digest,
                byte_size=byte_size,
                media_type=media_type,
            )
            created = self._initialize_master(document_id, target, digest, source_text=source_text)
        except Exception:
            document = self.store.get_document(document_id)
            if document is None:
                shutil.rmtree(target_dir, ignore_errors=True)
            raise
        return {"document_id": document_id, "deduplicated": False, "candidate_facts_created": created}

    def _initialize_master(self, document_id: str, stored: Path, digest: str, *, source_text: str | None = None) -> int:
        if source_text is None:
            source_text = stored.read_text(encoding="utf-8-sig")
        regions = map_editable_regions(source_text, digest)
        self.store.add_template_regions(document_id, (region.to_dict() for region in regions))
        created = self.store.create_candidate_facts_for_regions(document_id, digest)
        if self.store.get_baseline(document_id) is None:
            self.store.upsert_baseline(
                document_id,
                {
                    "status": "pending",
                    "source_metrics": source_metrics(source_text, regions),
                },
            )
        return created

    def import_supporting(self, source: Path) -> dict[str, Any]:
        source = source.resolve(strict=True)
        byte_size, suffix = self._validate_source(source, master=False)
        digest = sha256_file(source)
        existing = self.store.find_document_by_digest("supporting", digest)
        if existing is not None:
            return {"document_id": existing["id"], "deduplicated": True}
        document_id = f"support-{digest[:16]}"
        target_dir = self.paths.supporting_documents / document_id
        target = target_dir / f"source{suffix}"
        target_dir.mkdir(parents=True, exist_ok=False)
        try:
            with source.open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            if sha256_file(target) != digest:
                raise RuntimeError("supporting document copy failed hash verification")
            media_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            self.store.register_document(
                document_id=document_id,
                kind="supporting",
                original_name=source.name,
                stored_path=target,
                sha256=digest,
                byte_size=byte_size,
                media_type=media_type,
            )
        except Exception:
            document = self.store.get_document(document_id)
            if document is None:
                shutil.rmtree(target_dir, ignore_errors=True)
            raise
        return {"document_id": document_id, "deduplicated": False}

    def verify_document(self, document: dict[str, Any]) -> str:
        path = self.store.document_path(document)
        if not path.is_file():
            status = "missing"
        elif sha256_file(path) != str(document["sha256"]):
            status = "mismatch"
        else:
            status = "verified"
        if status != document.get("integrity_status"):
            self.store.set_integrity(str(document["id"]), status)
        return status

    def verify_active_master(self) -> str:
        master = self.store.get_active_master()
        if master is None:
            return "missing"
        return self.verify_document(master)
