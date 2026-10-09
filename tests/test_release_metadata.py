"""Keep the checked-in package and release metadata consistent."""

import json
from pathlib import Path
import tomllib

from tasukura import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_release_versions_match():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    manifest = json.loads(
        (ROOT / ".release-please-manifest.json").read_text(encoding="utf-8")
    )

    assert project["version"] == __version__ == manifest["."]


def test_lockfile_project_version_matches():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = [p for p in lock["package"] if p["name"] == project["name"]]

    assert len(packages) == 1
    assert packages[0]["source"] == {"editable": "."}
    assert packages[0]["version"] == project["version"]
