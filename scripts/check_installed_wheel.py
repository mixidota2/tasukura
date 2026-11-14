"""Run canonical tests against an installed wheel, not the source checkout."""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import sys
import sysconfig
import tempfile
import tomllib


class WheelAuditError(RuntimeError):
    """The selected interpreter is not testing the intended installed package."""


def verify_files(source: Path, installed: Path) -> list[str]:
    """Require the complete installed package payload to match the checkout."""

    def files(root: Path) -> dict[str, Path]:
        return {
            str(path.relative_to(root)): path
            for path in root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        }

    expected, actual = files(source), files(installed)
    if not expected or expected.keys() != actual.keys():
        raise WheelAuditError("Installed package file list differs from src/tasukura")
    for name, path in expected.items():
        if path.read_bytes() != actual[name].read_bytes():
            raise WheelAuditError(f"Installed package bytes differ: {name}")
    return sorted(expected)


def audit_package(root: Path) -> dict[str, str | list[str]]:
    site = Path(sysconfig.get_path("purelib")).resolve()
    package = site / "tasukura"
    distribution = metadata.distribution("tasukura")
    installed = Path(str(distribution.locate_file("tasukura"))).resolve()
    if installed != package:
        raise WheelAuditError(
            "tasukura distribution is outside this venv's site-packages"
        )
    direct_url = distribution.read_text("direct_url.json")
    if direct_url and json.loads(direct_url).get("dir_info", {}).get("editable"):
        raise WheelAuditError("An editable tasukura installation cannot test a wheel")
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    if distribution.version != project["version"]:
        raise WheelAuditError("Installed version differs from the checkout version")
    files = verify_files(root / "src" / "tasukura", package)
    # Import all current Python modules before collection so source shadowing is
    # rejected before tests run. Also inspect any submodules added by the tests.
    for name in files:
        if name.endswith(".py"):
            parts = Path(name).with_suffix("").parts
            if parts[-1] == "__init__":
                parts = parts[:-1]
            importlib.import_module(".".join(("tasukura", *parts)))
    for name, module in tuple(sys.modules.items()):
        if name == "tasukura" or name.startswith("tasukura."):
            origin = getattr(module, "__file__", None)
            if not origin or not Path(origin).resolve().is_relative_to(package):
                raise WheelAuditError(f"Non-wheel import for {name}: {origin}")
    return {"version": distribution.version, "package": str(package), "files": files}


class WheelAudit:
    def __init__(self, root: Path):
        self.root = root
        self.skipped = False

    def pytest_runtest_logreport(self, report):
        self.skipped |= report.skipped

    def pytest_collectreport(self, report):
        self.skipped |= report.skipped

    def pytest_sessionfinish(self, session, exitstatus):
        audit_package(self.root)
        if self.skipped:
            session.exitstatus = 1


def isolate_environment(home: str) -> None:
    os.environ["HOME"] = home
    for key in ("TK_DB_PATH", "TK_CONFIG_PATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        os.environ.pop(key, None)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    # Match ordinary clean configuration tests without using a user's HOME or
    # allowing a caller's database override to alter the test expectations.
    with tempfile.TemporaryDirectory(prefix="tasukura-wheel-home-") as home:
        isolate_environment(home)
        os.chdir(root)
        try:
            print("Wheel audit:", json.dumps(audit_package(root)))
        except (WheelAuditError, metadata.PackageNotFoundError) as error:
            print(f"Wheel audit failed: {error}", file=sys.stderr)
            return 1
        import pytest

        return int(
            pytest.main(
                ["-v", "-ra", "--import-mode=importlib", "tests"],
                plugins=[WheelAudit(root)],
            )
        )


if __name__ == "__main__":
    raise SystemExit(main())
