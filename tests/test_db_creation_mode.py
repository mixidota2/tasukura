"""POSIX creation-mode and recovery regressions using real SQLite processes."""

import os
import stat
import subprocess
import sys

import pytest

from tasukura.db import TaskDB

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")


def test_memory_database_does_not_create_a_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with TaskDB(":memory:") as db:
        assert db._conn.execute("PRAGMA database_list").fetchone()[2] == ""
        assert db._conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("existing", [False, True])
def test_relative_symlink_uses_private_target(tmp_path, existing):
    target = tmp_path / "target.db"
    link = tmp_path / "link.db"
    if existing:
        with TaskDB(target) as db:
            db._conn.execute("CREATE TABLE marker (value TEXT)")
            db._conn.execute("INSERT INTO marker VALUES ('keep')")
            db._conn.commit()
    link.symlink_to(target.name)
    old_mask = os.umask(0o022)
    try:
        with TaskDB(link) as db:
            assert link.is_symlink()
            for suffix in ("", "-wal", "-shm"):
                assert (
                    stat.S_IMODE(target.with_name(target.name + suffix).stat().st_mode)
                    == 0o600
                )
            assert db._conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            if existing:
                assert db._conn.execute("SELECT value FROM marker").fetchall() == [
                    ("keep",)
                ]
    finally:
        os.umask(old_mask)


@pytest.mark.parametrize("mask", [0o022, 0o077])
def test_new_database_and_live_sidecars_are_private(tmp_path, mask):
    path = tmp_path / "new" / "tasks.db"
    old_mask = os.umask(mask)
    try:
        with TaskDB(path) as first, TaskDB(path) as second:
            for suffix in ("", "-wal", "-shm"):
                assert (
                    stat.S_IMODE(path.with_name(path.name + suffix).stat().st_mode)
                    == 0o600
                )
            assert first._conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert second._conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        os.umask(old_mask)


@pytest.mark.parametrize("legacy", [False, True])
def test_abrupt_exit_recovers_without_rejecting_legacy_sidecars(tmp_path, legacy):
    path = tmp_path / "tasks.db"
    script = """
import os, sqlite3, sys
from tasukura.db import TaskDB
os.umask(0o022)
path, legacy = sys.argv[1:]
if legacy == 'True':
    conn = sqlite3.connect(path)
    conn.execute('PRAGMA journal_mode=WAL')
else:
    db = TaskDB(path)
    conn = db._conn
conn.execute('CREATE TABLE recovery_probe (value TEXT)')
conn.execute("INSERT INTO recovery_probe VALUES ('committed')")
conn.commit()
os.chmod(path, 0o600)
conn.execute("INSERT INTO recovery_probe VALUES ('uncommitted')")
os._exit(17)
"""
    result = subprocess.run([sys.executable, "-c", script, str(path), str(legacy)])
    assert result.returncode == 17
    expected = 0o644 if legacy else 0o600
    assert stat.S_IMODE(path.with_name(path.name + "-wal").stat().st_mode) == expected
    with TaskDB(path) as db:
        assert db._conn.execute("SELECT value FROM recovery_probe").fetchall() == [
            ("committed",)
        ]
        assert db._conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert stat.S_IMODE(path.with_name(path.name + "-wal").stat().st_mode) == 0o600


def test_concurrent_first_creation_keeps_private_files(tmp_path):
    """First-open contention must not truncate data or relax file modes.

    SQLite may reject a concurrent WAL-mode transition with 'database is
    locked'. This test does not promise successful parallel initialization.
    """
    script = """
import multiprocessing as mp, os, sqlite3, stat, sys
from pathlib import Path
from tasukura.db import TaskDB
path = Path(sys.argv[1])
ctx = mp.get_context('fork')
start = ctx.Barrier(4)
release = ctx.Event()
results = ctx.Queue()
def worker():
    os.umask(0o022)
    start.wait(timeout=10)
    try:
        db = TaskDB(path)
    except sqlite3.OperationalError as exc:
        results.put(('locked' if str(exc) == 'database is locked' else str(exc)))
        return
    results.put('ok')
    release.wait(timeout=10)
    db.close()
workers = [ctx.Process(target=worker) for _ in range(4)]
try:
    for worker_process in workers:
        worker_process.start()
    outcomes = [results.get(timeout=15) for _ in workers]
    assert 'ok' in outcomes, outcomes
    assert set(outcomes) <= {'ok', 'locked'}, outcomes
    for suffix in ('', '-wal', '-shm'):
        assert stat.S_IMODE(Path(str(path) + suffix).stat().st_mode) == 0o600
finally:
    release.set()
    for worker_process in workers:
        worker_process.join(timeout=15)
        if worker_process.is_alive():
            worker_process.kill()
            worker_process.join()
assert all(p.exitcode == 0 for p in workers)
with TaskDB(path) as db:
    assert db._conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert db._conn.execute("SELECT count(*) FROM tasks").fetchone()[0] == 0
"""
    subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "tasks.db")],
        check=True,
        timeout=60,
    )
