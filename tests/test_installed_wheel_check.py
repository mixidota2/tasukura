"""Regression tests for the wheel runner's provenance and failure checks."""

import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


SPEC = importlib.util.spec_from_file_location(
    "wheel_check",
    Path(__file__).resolve().parents[1] / "scripts" / "check_installed_wheel.py",
)
assert SPEC and SPEC.loader
wheel_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wheel_check)


@pytest.fixture
def package(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    source = root / "src" / "tasukura"
    site = tmp_path / "venv" / "site-packages"
    installed = site / "tasukura"
    source.mkdir(parents=True)
    installed.mkdir(parents=True)
    (root / "pyproject.toml").write_text('[project]\nversion = "0.1.11"\n')
    for folder in (source, installed):
        (folder / "__init__.py").write_text('__version__ = "0.1.11"\n')
        (folder / "module.py").write_text("answer = 42\n")
        (folder / "py.typed").write_text("")
    dist = SimpleNamespace(
        version="0.1.11",
        locate_file=lambda name: site / name,
        read_text=lambda name: None,
    )
    monkeypatch.setattr(wheel_check.metadata, "distribution", lambda name: dist)
    monkeypatch.setattr(wheel_check.sysconfig, "get_path", lambda name: str(site))
    for name in tuple(sys.modules):
        if name == "tasukura" or name.startswith("tasukura."):
            monkeypatch.delitem(sys.modules, name)
    for name, file in [("tasukura", "__init__.py"), ("tasukura.module", "module.py")]:
        monkeypatch.setitem(
            sys.modules, name, SimpleNamespace(__file__=str(installed / file))
        )
    original_import = wheel_check.importlib.import_module
    monkeypatch.setattr(
        wheel_check.importlib,
        "import_module",
        lambda name: (
            sys.modules[name] if name.startswith("tasukura") else original_import(name)
        ),
    )
    return SimpleNamespace(root=root, source=source, installed=installed, dist=dist)


def test_valid_wheel_audit(package):
    result = wheel_check.audit_package(package.root)
    assert result["version"] == "0.1.11"
    assert result["files"] == ["__init__.py", "module.py", "py.typed"]


@pytest.mark.parametrize("mutation", ["missing", "extra", "bytes"])
def test_rejects_mismatched_payload(package, mutation):
    if mutation == "missing":
        (package.installed / "py.typed").unlink()
    elif mutation == "extra":
        (package.installed / "unexpected.py").write_text("extra = 1\n")
    else:
        (package.installed / "module.py").write_text("answer = 0\n")
    with pytest.raises(wheel_check.WheelAuditError, match="file list|bytes differ"):
        wheel_check.audit_package(package.root)


def test_empty_payload_does_not_pass(tmp_path):
    with pytest.raises(wheel_check.WheelAuditError, match="file list"):
        wheel_check.verify_files(tmp_path / "source", tmp_path / "installed")


def test_generated_cache_is_not_package_drift(package):
    cache = package.installed / "__pycache__"
    cache.mkdir()
    (cache / "module.cpython-313.pyc").write_bytes(b"generated")
    assert len(wheel_check.audit_package(package.root)["files"]) == 3


def test_rejects_wrong_version(package):
    package.dist.version = "0.1.10"
    with pytest.raises(wheel_check.WheelAuditError, match="version"):
        wheel_check.audit_package(package.root)


def test_rejects_editable_install(package):
    package.dist.read_text = lambda name: '{"dir_info": {"editable": true}}'
    with pytest.raises(wheel_check.WheelAuditError, match="editable"):
        wheel_check.audit_package(package.root)


def test_accepts_local_wheel_direct_url(package):
    package.dist.read_text = lambda name: (
        '{"url": "file:///tmp/package.whl", "archive_info": {}}'
    )
    assert wheel_check.audit_package(package.root)["version"] == "0.1.11"


def test_rejects_distribution_outside_venv(package):
    package.dist.locate_file = lambda name: package.source
    with pytest.raises(wheel_check.WheelAuditError, match="outside"):
        wheel_check.audit_package(package.root)


@pytest.mark.parametrize("module", ["tasukura", "tasukura.module"])
def test_rejects_source_shadowing(package, module):
    sys.modules[module].__file__ = str(package.source / "__init__.py")
    with pytest.raises(wheel_check.WheelAuditError, match="Non-wheel import"):
        wheel_check.audit_package(package.root)


@pytest.mark.parametrize("hook", ["pytest_collectreport", "pytest_runtest_logreport"])
def test_skip_is_a_failed_gate(package, hook):
    audit = wheel_check.WheelAudit(package.root)
    getattr(audit, hook)(SimpleNamespace(skipped=True))
    session = SimpleNamespace(exitstatus=0)
    audit.pytest_sessionfinish(session, 0)
    assert session.exitstatus == 1


@pytest.mark.parametrize("status", [0, 1, 5])
def test_preserves_pytest_exit_status(package, status):
    audit = wheel_check.WheelAudit(package.root)
    audit.pytest_runtest_logreport(SimpleNamespace(skipped=False))
    session = SimpleNamespace(exitstatus=status)
    audit.pytest_sessionfinish(session, status)
    assert session.exitstatus == status


def test_isolation_removes_inherited_config_and_pytest_options(tmp_path, monkeypatch):
    for key in (
        "HOME",
        "TK_DB_PATH",
        "TK_CONFIG_PATH",
        "PYTEST_ADDOPTS",
        "PYTEST_PLUGINS",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    ):
        monkeypatch.setenv(key, "outside-value")
    monkeypatch.setenv("UNRELATED_SETTING", "preserved")
    wheel_check.isolate_environment(str(tmp_path))
    assert os.environ["HOME"] == str(tmp_path)
    for key in ("TK_DB_PATH", "TK_CONFIG_PATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        assert key not in os.environ
    assert os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert os.environ["UNRELATED_SETTING"] == "preserved"
