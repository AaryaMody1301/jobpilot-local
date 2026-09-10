from pathlib import Path

import pytest

from jobpilot.runtime.paths import ManagedPaths, UnsafeManagedPath


def test_model_root_itself_cannot_be_deleted(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "app")
    paths.create_phase0_roots()
    with pytest.raises(UnsafeManagedPath):
        paths.delete_model_path(paths.models)
    assert paths.models.exists()


def test_parent_traversal_cannot_escape_model_root(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "app")
    paths.create_phase0_roots()
    outside = paths.models / ".." / "do-not-delete.txt"
    outside.resolve().write_text("keep", encoding="utf-8")
    with pytest.raises(UnsafeManagedPath):
        paths.delete_model_path(outside)
    assert outside.resolve().read_text(encoding="utf-8") == "keep"


def test_managed_model_descendant_can_be_deleted(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "app")
    paths.create_phase0_roots()
    model = paths.models / "catalogue-entry" / "model.gguf"
    model.parent.mkdir()
    model.write_bytes(b"fixture")
    paths.delete_model_path(model.parent)
    assert not model.parent.exists()


def test_symlink_resolving_outside_is_rejected(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "app")
    paths.create_phase0_roots()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "model.gguf"
    target.write_bytes(b"keep")
    link = paths.models / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")
    with pytest.raises(UnsafeManagedPath):
        paths.delete_model_path(link)
    assert target.exists()
