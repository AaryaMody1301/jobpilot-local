from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import shutil
from pathlib import Path
from typing import Any

from jobpilot.resume.facts import extract_protected_facts
from jobpilot.resume.store import ResumeStore
from jobpilot.resume.template_map import EXTERNAL_INPUT_RE, map_editable_regions, source_metrics
from jobpilot.runtime.paths import ManagedPaths

MASTER_MAX_BYTES = 10 * 1024 * 1024
SUPPORTING_MAX_BYTES = 40 * 1024 * 1024
SUPPORTING_SUFFIXES = {".pdf", ".txt", ".md", ".tex"}
TEMPLATE_SUFFIXES = {".tex", ".sty", ".cls", ".pdf", ".png", ".jpg", ".jpeg", ".bib"}
TEMPLATE_MAX_FILES = 64
TEMPLATE_MAX_BYTES = 25 * 1024 * 1024
LOCAL_PACKAGE_RE = re.compile(r"\\usepackage(?:\[[^]]*\])?\{([^}]*)\}")
LOCAL_CLASS_RE = re.compile(r"\\documentclass(?:\[[^]]*\])?\{([^}]*)\}")


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
        try:
            source_text = source.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("the .tex resume must be UTF-8 text") from exc
        dependencies = self._local_dependencies(source, source_text)
        existing = self.store.find_document_by_digest("master_resume", digest)
        if existing is not None:
            stored = self.store.document_path(existing)
            if not stored.is_file() or sha256_file(stored) != digest:
                self.store.set_integrity(str(existing["id"]), "missing" if not stored.exists() else "mismatch")
                raise RuntimeError("the previously imported immutable master no longer matches its recorded hash")
            self._install_template_bundle(str(existing["id"]), stored, digest, dependencies)
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
            self._install_template_bundle(document_id, target, digest, dependencies)
            created = self._initialize_master(document_id, target, digest, source_text=source_text)
        except Exception:
            document = self.store.get_document(document_id)
            if document is None:
                shutil.rmtree(target_dir, ignore_errors=True)
            raise
        return {"document_id": document_id, "deduplicated": False, "candidate_facts_created": created}

    @staticmethod
    def _safe_local_path(root: Path, candidate: str) -> Path:
        if not candidate or "\\" in candidate or ":" in candidate or Path(candidate).is_absolute() or ".." in Path(candidate).parts:
            raise ValueError(f"unsafe local template dependency: {candidate[:100]}")
        path = root / candidate
        relative = path.relative_to(root)
        if any(item.is_symlink() for item in (root / Path(*relative.parts[:n]) for n in range(1, len(relative.parts) + 1))):
            raise ValueError(f"template dependency is a symbolic link: {candidate[:100]}")
        if not path.resolve(strict=False).is_relative_to(root.resolve(strict=True)):
            raise ValueError("template dependency escaped its source folder")
        return path

    def _local_dependencies(self, source: Path, source_text: str) -> dict[str, Path]:
        root = source.parent
        found: dict[str, Path] = {}
        total_bytes = 0
        pending = [(source_text, root)]
        while pending:
            text, parent = pending.pop()
            references: list[tuple[str, str]] = []
            for match in EXTERNAL_INPUT_RE.finditer(text):
                command = match.group(0).split("{")[0]
                suffix = ".png" if "includegraphics" in command else ".bib" if "bibliography" in command else ".tex"
                references.append((match.group(1).strip(), suffix))
            for match in LOCAL_PACKAGE_RE.finditer(text):
                references.extend((name.strip(), ".sty") for name in match.group(1).split(","))
            for match in LOCAL_CLASS_RE.finditer(text):
                references.append((match.group(1).strip(), ".cls"))
            for name, suffix in references:
                if not name:
                    continue
                self._safe_local_path(root, name)
                candidate = self._safe_local_path(root, (parent / name).relative_to(root).as_posix())
                if not candidate.suffix:
                    variants = [candidate.with_suffix(ext) for ext in ((".pdf", ".png", ".jpg", ".jpeg") if suffix == ".png" else (suffix,))]
                    available = [item for item in variants if item.is_file()]
                    candidate = available[0] if available else variants[0]
                candidate = self._safe_local_path(root, candidate.relative_to(root).as_posix())
                if not candidate.is_file():
                    # Tectonic may provide an input as well as a class/package from its cache.
                    # A genuinely missing local file is reported by the baseline compile.
                    continue
                if candidate.suffix.lower() not in TEMPLATE_SUFFIXES:
                    raise ValueError(f"unsupported local template file type: {candidate.suffix}")
                relative = candidate.relative_to(root).as_posix()
                if candidate == source or relative in found:
                    continue
                total_bytes += candidate.stat().st_size
                if len(found) >= TEMPLATE_MAX_FILES or total_bytes > TEMPLATE_MAX_BYTES:
                    raise ValueError("local template dependencies exceed the file or size limit")
                found[relative] = candidate
                if candidate.suffix.lower() in {".tex", ".sty", ".cls"}:
                    try:
                        pending.append((candidate.read_text(encoding="utf-8-sig"), candidate.parent))
                    except UnicodeDecodeError as exc:
                        raise ValueError(f"local template dependency is not UTF-8: {relative}") from exc
        return found

    def _install_template_bundle(self, document_id: str, master_path: Path, digest: str, dependencies: dict[str, Path]) -> None:
        if not dependencies:
            if self.store.active_template_bundle(document_id):
                self.store.set_active_template_bundle(document_id, None)
            return
        evidence = {name: {"sha256": sha256_file(path), "bytes": path.stat().st_size} for name, path in sorted(dependencies.items())}
        manifest = {"master_sha256": digest, "files": evidence}
        encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
        bundle_id = hashlib.sha256(encoded).hexdigest()
        bundle_parent = master_path.parent / "bundles"
        root = bundle_parent / bundle_id
        if bundle_parent.is_symlink() or root.is_symlink():
            raise RuntimeError("template bundle storage is not an app-managed directory")
        root.mkdir(parents=True, exist_ok=True)
        source_copy = root / "source.tex"
        if not source_copy.exists():
            shutil.copyfile(master_path, source_copy)
        for name, original in dependencies.items():
            target = self._safe_local_path(root, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copyfile(original, target)
        manifest_path = root / "manifest.json"
        if not manifest_path.exists():
            manifest_path.write_bytes(encoded)
        self._verify_bundle_files(root, bundle_id, digest)
        if self.store.active_template_bundle(document_id) != bundle_id:
            self.store.set_active_template_bundle(document_id, bundle_id)

    def verified_bundle(self, master: dict[str, Any]) -> tuple[Path, dict[str, dict[str, Any]]] | None:
        bundle_id = self.store.active_template_bundle(str(master["id"]))
        if bundle_id is None:
            return None
        master_root = self.store.document_path(master).parent
        bundle_parent = master_root / "bundles"
        root = bundle_parent / bundle_id
        if bundle_parent.is_symlink() or root.is_symlink() or not root.resolve(strict=False).is_relative_to(master_root.resolve(strict=True)):
            raise RuntimeError("immutable template bundle path failed integrity verification")
        return root, self._verify_bundle_files(root, bundle_id, str(master["sha256"]))

    def _verify_bundle_files(self, root: Path, bundle_id: str, digest: str) -> dict[str, dict[str, Any]]:
        manifest_path = root / "manifest.json"
        if not re.fullmatch(r"[0-9a-f]{64}", bundle_id) or manifest_path.is_symlink() or not manifest_path.is_file() or sha256_file(manifest_path) != bundle_id:
            raise RuntimeError("immutable template bundle manifest failed integrity verification")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = manifest["files"]
            if manifest["master_sha256"] != digest or not isinstance(files, dict) or len(files) > TEMPLATE_MAX_FILES:
                raise ValueError("invalid template manifest")
            source = root / "source.tex"
            if source.is_symlink() or sha256_file(source) != digest:
                raise ValueError("template source copy changed")
            for name, evidence in files.items():
                path = self._safe_local_path(root, name)
                if path.suffix.lower() not in TEMPLATE_SUFFIXES or not path.is_file() or path.stat().st_size != evidence["bytes"] or sha256_file(path) != evidence["sha256"]:
                    raise ValueError(f"template dependency changed: {name}")
            return files
        except Exception as exc:
            raise RuntimeError(f"immutable template dependencies failed integrity verification: {str(exc)[:200]}") from exc

    def _initialize_master(self, document_id: str, stored: Path, digest: str, *, source_text: str | None = None) -> int:
        if source_text is None:
            source_text = stored.read_text(encoding="utf-8-sig")
        regions = map_editable_regions(source_text, digest)
        self.store.add_template_regions(document_id, (region.to_dict() for region in regions))
        created = self.store.create_candidate_facts_for_regions(document_id, digest)

        existing_ids = {str(fact["id"]) for fact in self.store.list_facts()}
        for candidate in extract_protected_facts(source_text, digest):
            if candidate.fact_id in existing_ids:
                continue
            self.store.create_fact(
                fact_id=candidate.fact_id,
                value=candidate.value,
                category=candidate.category,
                source_document_id=document_id,
                source_ref=candidate.source_ref(digest),
            )
            existing_ids.add(candidate.fact_id)
            created += 1

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
