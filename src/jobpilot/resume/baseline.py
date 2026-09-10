from __future__ import annotations

import hashlib
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from jobpilot.resume.documents import sha256_file
from jobpilot.resume.store import ResumeStore
from jobpilot.resume.tectonic import TectonicCompiler
from jobpilot.resume.template_map import map_editable_regions, source_metrics
from jobpilot.resume.tooling import TECTONIC_VERSION, TectonicInstallService, resolve_tectonic_executable
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.runtime.process_supervisor import ProcessSupervisor
from jobpilot.storage.database import utc_now_text

COMPILE_TIMEOUT_SECONDS = 120.0


def _relative_to_root(paths: ManagedPaths, path: Path) -> str:
    return path.resolve(strict=False).relative_to(paths.root.resolve(strict=False)).as_posix()


def inspect_pdf(pdf_path: Path) -> dict[str, Any]:
    reader = PdfReader(str(pdf_path))
    page_sizes: list[dict[str, float]] = []
    extracted: list[str] = []
    for page in reader.pages:
        page_sizes.append({
            "width": round(float(page.mediabox.width), 3),
            "height": round(float(page.mediabox.height), 3),
        })
        extracted.append(page.extract_text() or "")
    text = "\n".join(extracted).strip()
    return {
        "page_count": len(reader.pages),
        "page_sizes": page_sizes,
        "text": text,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


class ResumeBaselineService:
    def __init__(self, paths: ManagedPaths, store: ResumeStore) -> None:
        self.paths = paths
        self.store = store

    def compile_active(self, *, allow_package_downloads: bool, cancel_event: threading.Event | None = None) -> dict[str, Any]:
        document = self.store.get_active_master()
        if document is None:
            raise RuntimeError("import a master .tex resume before compiling a baseline")
        source = self.store.document_path(document)
        if not source.is_file() or sha256_file(source) != str(document["sha256"]):
            self.store.set_integrity(str(document["id"]), "missing" if not source.exists() else "mismatch")
            raise RuntimeError("master resume integrity verification failed; re-import the source before compiling")
        tool_status = TectonicInstallService(self.paths).status()
        executable = resolve_tectonic_executable(self.paths)
        if not tool_status.get("installed") or tool_status.get("integrity") != "verified" or executable is None:
            raise RuntimeError("Tectonic is not installed with verified app-managed metadata; use the explicit Install Tectonic action first")

        document_id = str(document["id"])
        outdir = source.parent / "baseline"
        outdir.mkdir(parents=True, exist_ok=True)
        expected_pdf = outdir / f"{source.stem}.pdf"
        expected_log = outdir / f"{source.stem}.log"
        expected_pdf.unlink(missing_ok=True)
        expected_log.unlink(missing_ok=True)

        compiler = TectonicCompiler(executable, self.paths.tectonic_cache)
        command = compiler.build_command(source, outdir, allow_package_downloads=allow_package_downloads)
        supervisor = ProcessSupervisor()
        process = supervisor.spawn(command, cwd=source.parent, env=compiler.environment())
        try:
            deadline = time.monotonic() + COMPILE_TIMEOUT_SECONDS
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    supervisor.terminate_owned()
                    error = "Tectonic baseline compilation was cancelled"
                    self._record_failure(document_id, source, expected_log, error)
                    raise RuntimeError(error)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    supervisor.terminate_owned()
                    error = f"Tectonic compile exceeded {int(COMPILE_TIMEOUT_SECONDS)} seconds"
                    self._record_failure(document_id, source, expected_log, error)
                    raise RuntimeError(error)
                try:
                    return_code = process.wait(timeout=min(0.2, remaining))
                    break
                except (TimeoutError, subprocess.TimeoutExpired):
                    continue
        finally:
            supervisor.close()

        if return_code != 0 or not expected_pdf.is_file():
            log_tail = ""
            if expected_log.is_file():
                log_tail = expected_log.read_text(encoding="utf-8", errors="replace")[-4000:].strip()
            error = log_tail or f"Tectonic exited with code {return_code} and produced no baseline PDF"
            self._record_failure(document_id, source, expected_log, error)
            raise RuntimeError(error)

        pdf = inspect_pdf(expected_pdf)
        source_text = source.read_text(encoding="utf-8-sig")
        regions = map_editable_regions(source_text, str(document["sha256"]))
        metrics = source_metrics(source_text, regions)
        if pdf["page_count"] < 1:
            error = "compiled baseline PDF contains no pages"
            self._record_failure(document_id, source, expected_log, error)
            raise RuntimeError(error)
        if not str(pdf["text"]).strip():
            error = "compiled baseline PDF contains no extractable text; baseline validation cannot continue"
            self._record_failure(document_id, source, expected_log, error)
            raise RuntimeError(error)

        compiled_at = utc_now_text()
        values = {
            "status": "compiled",
            "compiler_version": TECTONIC_VERSION,
            "page_count": pdf["page_count"],
            "page_sizes": pdf["page_sizes"],
            "pdf_relpath": _relative_to_root(self.paths, expected_pdf),
            "pdf_sha256": sha256_file(expected_pdf),
            "text_sha256": pdf["text_sha256"],
            "source_metrics": metrics,
            "compile_log_relpath": _relative_to_root(self.paths, expected_log) if expected_log.is_file() else None,
            "compile_error": None,
            "offline_verified": not allow_package_downloads,
            "last_compile_used_network": allow_package_downloads,
            "compiled_at": compiled_at,
        }
        self.store.upsert_baseline(document_id, values)
        return values

    def _record_failure(self, document_id: str, source: Path, log: Path, error: str) -> None:
        source_text = source.read_text(encoding="utf-8-sig", errors="replace")
        document = self.store.get_document(document_id)
        digest = str(document["sha256"]) if document else "unknown"
        regions = map_editable_regions(source_text, digest)
        self.store.upsert_baseline(
            document_id,
            {
                "status": "failed",
                "compiler_version": TECTONIC_VERSION,
                "source_metrics": source_metrics(source_text, regions),
                "compile_log_relpath": _relative_to_root(self.paths, log) if log.is_file() else None,
                "compile_error": error[-4000:],
                "offline_verified": False,
                "last_compile_used_network": False,
                "compiled_at": utc_now_text(),
            },
        )
