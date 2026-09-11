from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


class UnsafeManagedPath(ValueError):
    pass


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class ManagedPaths:
    root: Path

    @classmethod
    def default(cls) -> "ManagedPaths":
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return cls(base / "JobPilotLocal")

    @property
    def database_dir(self) -> Path:
        return self.root / "db"

    @property
    def database_file(self) -> Path:
        return self.database_dir / "jobpilot.sqlite3"

    @property
    def documents(self) -> Path:
        return self.root / "documents"

    @property
    def master_documents(self) -> Path:
        return self.documents / "master"

    @property
    def supporting_documents(self) -> Path:
        return self.documents / "supporting"

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts"

    @property
    def application_artifacts(self) -> Path:
        return self.artifacts / "applications"

    @property
    def models(self) -> Path:
        return self.root / "models"

    @property
    def tools(self) -> Path:
        return self.root / "tools"

    @property
    def tectonic_tool_dir(self) -> Path:
        return self.tools / "tectonic" / "0.17.0"

    @property
    def tectonic_executable(self) -> Path:
        return self.tectonic_tool_dir / "tectonic.exe"

    @property
    def tectonic_metadata(self) -> Path:
        return self.tectonic_tool_dir / "install.json"

    @property
    def browsers(self) -> Path:
        return self.root / "browsers"

    @property
    def browser_profile(self) -> Path:
        return self.root / "browser-profile"

    @property
    def tectonic_cache(self) -> Path:
        return self.root / "tectonic" / "cache"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def runtime(self) -> Path:
        return self.root / "runtime"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    def create_phase0_roots(self) -> None:
        for path in (self.models, self.browsers, self.tectonic_cache, self.runtime):
            path.mkdir(parents=True, exist_ok=True)

    def create_all_roots(self) -> None:
        for path in (
            self.database_dir,
            self.master_documents,
            self.supporting_documents,
            self.application_artifacts,
            self.models,
            self.tools,
            self.browsers,
            self.browser_profile,
            self.tectonic_cache,
            self.backups,
            self.cache,
            self.runtime,
            self.logs,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _require_descendant(candidate: Path, root: Path, label: str) -> Path:
        managed_root = root.resolve(strict=False)
        resolved = candidate.resolve(strict=False)
        if resolved == managed_root or not _is_relative_to(resolved, managed_root):
            raise UnsafeManagedPath(f"path is outside managed {label}: {candidate}")
        return resolved

    def relative_to_root(self, candidate: Path) -> Path:
        """Return a stable app-root-relative path after canonicalizing both sides.

        On Windows the same directory can appear through an 8.3 short path on one
        side and an expanded long path on the other. Canonicalizing both paths keeps
        the containment proof strict without rejecting that legitimate alias.
        """
        managed_root = self.root.resolve(strict=False)
        resolved = candidate.resolve(strict=False)
        if resolved == managed_root or not _is_relative_to(resolved, managed_root):
            raise UnsafeManagedPath(f"path is outside the JobPilot managed root: {candidate}")
        return resolved.relative_to(managed_root)

    def require_model_descendant(self, candidate: Path) -> Path:
        return self._require_descendant(candidate, self.models, "model files")

    def require_tool_descendant(self, candidate: Path) -> Path:
        return self._require_descendant(candidate, self.tools, "tool files")

    @staticmethod
    def _delete_descendant(resolved: Path) -> None:
        if not resolved.exists():
            return
        if resolved.is_dir():
            shutil.rmtree(resolved)
        else:
            resolved.unlink()

    def delete_model_path(self, candidate: Path) -> None:
        self._delete_descendant(self.require_model_descendant(candidate))

    def delete_tool_path(self, candidate: Path) -> None:
        self._delete_descendant(self.require_tool_descendant(candidate))
