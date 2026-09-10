from __future__ import annotations

import hashlib
import threading
import zipfile
from pathlib import Path

import pytest

from jobpilot.model.catalogue import CATALOGUE_VERSION, MODELS, RUNTIMES, get_model, get_runtime
from jobpilot.model.downloads import ArtifactIntegrityError, DownloadCancelled, download_verified, extract_zip_verified
from jobpilot.model.hardware import HardwareProbe
from jobpilot.model.runtime import LlamaRuntimeSession


def test_catalogue_is_small_versioned_and_content_pinned() -> None:
    assert CATALOGUE_VERSION == "2026-09-10.1"
    assert 1 <= len(MODELS) <= 4
    assert 1 <= len(RUNTIMES) <= 4
    for model in MODELS:
        assert len(model.sha256) == 64
        int(model.sha256, 16)
        assert model.url.startswith("https://huggingface.co/")
        assert model.license == "Apache-2.0"
        assert model.tested_context_tokens == 4096
        assert get_model(model.id) is model
    for runtime in RUNTIMES:
        assert len(runtime.sha256) == 64
        int(runtime.sha256, 16)
        assert runtime.url.startswith("https://github.com/ggml-org/llama.cpp/releases/download/b10809/")
        assert runtime.version == "0.4.0"
        assert get_runtime(runtime.id) is runtime


def test_hardware_probe_creates_conservative_single_inference_budget(tmp_path: Path) -> None:
    snapshot = HardwareProbe(tmp_path).capture().to_dict()
    assert snapshot["memory"]["total_bytes"] > 0
    assert 0 <= snapshot["budget"]["model_ram_budget_bytes"] <= snapshot["memory"]["total_bytes"]
    assert snapshot["budget"]["model_disk_budget_bytes"] >= 0
    assert snapshot["budget"]["max_concurrent_inference"] == 1
    assert snapshot["budget"]["memory_pressure"] in {"normal", "constrained", "critical"}
    for gpu in snapshot["gpus"]:
        if gpu["total_vram_bytes"] is not None:
            assert gpu["total_vram_bytes"] > 0
        assert gpu["evidence"]


def test_verified_download_is_atomic_and_rejects_wrong_hash(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"phase3-artifact")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    destination = tmp_path / "dest" / "artifact.bin"
    size = download_verified(url=source.resolve().as_uri(), destination=destination, expected_sha256=digest, expected_bytes=source.stat().st_size, cancel_event=threading.Event())
    assert size == source.stat().st_size
    assert destination.read_bytes() == source.read_bytes()
    assert not destination.with_suffix(".bin.part").exists()
    destination.unlink()
    with pytest.raises(ArtifactIntegrityError):
        download_verified(url=source.resolve().as_uri(), destination=destination, expected_sha256="0" * 64, expected_bytes=source.stat().st_size, cancel_event=threading.Event())
    assert not destination.exists()


def test_download_honors_preexisting_cancel(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"cancel")
    cancel = threading.Event(); cancel.set()
    with pytest.raises(DownloadCancelled):
        download_verified(url=source.resolve().as_uri(), destination=tmp_path / "dest.bin", expected_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), expected_bytes=len(source.read_bytes()), cancel_event=cancel)


def test_zip_extraction_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape.txt", "no")
    with pytest.raises(ArtifactIntegrityError):
        extract_zip_verified(archive, tmp_path / "install")
    assert not (tmp_path / "escape.txt").exists()


def test_llama_runtime_session_slots_construct_before_start(tmp_path: Path) -> None:
    session = LlamaRuntimeSession(executable=tmp_path / "llama-server.exe", model_path=tmp_path / "model.gguf", backend="cpu", context_tokens=4096, threads=2)
    assert session.pid is None
    with pytest.raises(RuntimeError, match="not started"):
        _ = session.base_url
