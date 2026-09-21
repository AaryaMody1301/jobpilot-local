from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from jobpilot.applications.platforms import LeverAdapter
from jobpilot.pilot import LiveHostedFormEngine
from jobpilot.runtime.paths import ManagedPaths


class _TailoringStore:
    def __init__(self, root: Path, run: dict[str, object]) -> None:
        self.root = root.resolve(strict=False)
        self.run = run

    def get_run(self, run_id: str) -> dict[str, object] | None:
        return self.run if run_id == self.run.get("id") else None

    def absolute_path(self, relative: str) -> Path:
        resolved = (self.root / relative).resolve(strict=False)
        if resolved == self.root or not resolved.is_relative_to(self.root):
            raise ValueError("tailoring artifact path escaped the app-managed root")
        return resolved


class _BodyLocator:
    def __init__(self, page: "_ConfirmationPage") -> None:
        self.page = page

    def inner_text(self) -> str:
        return self.page.body


class _MarkerLocator:
    def __init__(self, page: "_ConfirmationPage") -> None:
        self.page = page

    def count(self) -> int:
        return self.page.marker_count


class _SubmitLocator:
    def __init__(self, page: "_ConfirmationPage") -> None:
        self.page = page

    def click(self, *, timeout: int) -> None:
        assert timeout == 5000
        self.page.submit_clicked = True


class _ConfirmationPage:
    def __init__(self, *, body: str, marker_count: int = 0, allow_confirmation: bool = False) -> None:
        self.url = "https://jobs.lever.co/example/apply"
        self.body = body
        self.marker_count = marker_count
        self.allow_confirmation = allow_confirmation
        self.seen_baseline: dict[str, object] | None = None
        self.submit_clicked = False

    def locator(self, selector: str):
        if selector == "body":
            return _BodyLocator(self)
        if selector == '[data-jobpilot-confirmation="success"]':
            return _MarkerLocator(self)
        raise AssertionError(f"unexpected selector: {selector}")

    def wait_for_function(self, script: str, *, arg: dict[str, object], timeout: int) -> None:
        assert "newMarker" in script and "newPhrase" in script
        assert timeout == 3000
        self.seen_baseline = arg
        if not self.allow_confirmation:
            raise TimeoutError("no new post-submit confirmation state")


def test_live_resume_upload_resolves_managed_pdf_relpath_and_rechecks_hash(tmp_path: Path) -> None:
    root = (tmp_path / "JobPilotLocal").resolve()
    pdf = root / "artifacts" / "applications" / "tailoring" / "run-1" / "resume.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"verified tailored resume")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    run = {
        "id": "run-1",
        "pdf_relpath": pdf.relative_to(root).as_posix(),
        "pdf_sha256": digest,
    }
    store = _TailoringStore(root, run)
    journal = SimpleNamespace(tailoring=SimpleNamespace(store=store))
    engine = LiveHostedFormEngine(ManagedPaths(root), journal, lambda: True)  # type: ignore[arg-type]

    assert engine._resume_path({"tailoring_run_id": "run-1"}) == pdf

    pdf.write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="integrity verification"):
        engine._resume_path({"tailoring_run_id": "run-1"})


def test_static_success_like_text_is_not_confirmation_without_new_state() -> None:
    page = _ConfirmationPage(body="Application received questions and FAQ", allow_confirmation=False)
    adapter = LeverAdapter(page, allow_live_submit=True)
    adapter._confirmation_baseline = adapter._confirmation_state()

    result = adapter.confirm()

    assert result.confirmed is False
    assert page.seen_baseline is not None
    assert "application received" in page.seen_baseline["phrases"]


def test_submit_recaptures_confirmation_baseline_immediately_before_click() -> None:
    page = _ConfirmationPage(body="Application form", allow_confirmation=False)
    adapter = LeverAdapter(page, allow_live_submit=True)
    adapter._confirmation_baseline = adapter._confirmation_state()
    adapter._submit = _SubmitLocator(page)

    page.body = "Application received questions and FAQ"
    adapter.submit()
    result = adapter.confirm()

    assert page.submit_clicked is True
    assert result.confirmed is False
    assert page.seen_baseline is not None
    assert "application received" in page.seen_baseline["phrases"]


def test_new_explicit_success_marker_can_confirm_after_baseline() -> None:
    page = _ConfirmationPage(body="Application form", marker_count=0, allow_confirmation=True)
    adapter = LeverAdapter(page, allow_live_submit=True)
    adapter._confirmation_baseline = adapter._confirmation_state()
    page.body = "Thank you for applying. Application submitted."
    page.marker_count = 1

    result = adapter.confirm()

    assert result.confirmed is True
    assert page.seen_baseline == {
        "url": "https://jobs.lever.co/example/apply",
        "marker_count": 0,
        "phrases": [],
    }
