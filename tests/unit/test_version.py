from pathlib import Path
import tomllib

import jobpilot
from jobpilot.version import __version__


ROOT = Path(__file__).resolve().parents[2]


def test_package_and_distribution_versions_share_one_value() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == __version__
    assert jobpilot.__version__ == __version__
