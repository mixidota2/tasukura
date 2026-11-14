"""Database initialization must not rewrite unrelated directory permissions."""

import os
import sqlite3
import stat

import pytest

from tasukura.db import TaskDB

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")


def mode(path):
    return stat.S_IMODE(path.stat().st_mode)


@pytest.mark.parametrize("parent_mode", [0o755, 0o750, 0o2770, 0o1777])
@pytest.mark.parametrize("existing", [False, True])
def test_existing_parent_permissions_are_preserved(tmp_path, parent_mode, existing):
    parent = tmp_path / "workspace"
    parent.mkdir()
    path = parent / "tasks.db"
    if existing:
        with TaskDB(path) as db:
            task = db.add_task("keep", "synthetic task")
    parent.chmod(parent_mode)
    with TaskDB(path) as db:
        assert mode(parent) == parent_mode
        assert mode(path) == 0o600
        assert db._conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        if existing:
            assert db.get_task(task.id).title == "keep"
    assert mode(parent) == parent_mode


@pytest.mark.parametrize("mask", [0o022, 0o077])
def test_new_parent_is_created_private_without_changing_ancestors(tmp_path, mask):
    shared = tmp_path / "shared"
    shared.mkdir()
    shared.chmod(0o755)
    path = shared / "nested" / "private" / "tasks.db"
    old_mask = os.umask(mask)
    try:
        with TaskDB(path):
            assert mode(path.parent) == 0o700
            assert mode(shared) == 0o755
            for suffix in ("", "-wal", "-shm"):
                assert mode(path.with_name(path.name + suffix)) == 0o600
    finally:
        os.umask(old_mask)


def test_memory_database_does_not_touch_cwd_or_literal_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o755)
    unrelated = tmp_path / ":memory:"
    unrelated.write_bytes(b"not a database; preserve this file\n")
    unrelated.chmod(0o644)
    with TaskDB(":memory:") as db:
        assert db._conn.execute("PRAGMA database_list").fetchone()[2] == ""
        task = db.add_task("memory only", "synthetic")
        assert db.get_task(task.id).title == "memory only"
    assert mode(tmp_path) == 0o755
    assert mode(unrelated) == 0o644
    assert unrelated.read_bytes() == b"not a database; preserve this file\n"
    assert list(tmp_path.iterdir()) == [unrelated]


def test_symlinked_parent_permissions_are_preserved(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir()
    shared.chmod(0o2770)
    link = tmp_path / "linked"
    link.symlink_to(shared, target_is_directory=True)
    with TaskDB(link / "tasks.db"):
        assert link.is_symlink()
        assert mode(shared) == 0o2770
        assert mode(shared / "tasks.db") == 0o600


def test_relative_database_does_not_chmod_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tmp_path.chmod(0o755)
    with TaskDB("tasks.db"):
        assert mode(tmp_path) == 0o755
        assert mode(tmp_path / "tasks.db") == 0o600


@pytest.mark.parametrize("live_wal", [False, True])
def test_legacy_database_is_private_before_sqlite_opens(
    tmp_path, monkeypatch, live_wal
):
    parent = tmp_path / "shared"
    parent.mkdir()
    parent.chmod(0o755)
    path = parent / "tasks.db"
    legacy = sqlite3.connect(path)
    if live_wal:
        legacy.execute("PRAGMA journal_mode=WAL")
    legacy.execute("CREATE TABLE marker (value TEXT)")
    legacy.execute("INSERT INTO marker VALUES ('keep')")
    legacy.commit()
    files = [path]
    if live_wal:
        files += [path.with_name(path.name + suffix) for suffix in ("-wal", "-shm")]
    for file in files:
        file.chmod(0o644)
    connect = sqlite3.connect
    calls = []

    def checked_connect(*args, **kwargs):
        assert mode(parent) == 0o755
        assert all(mode(file) == 0o600 for file in files)
        calls.append(True)
        return connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", checked_connect)
    try:
        with TaskDB(path) as db:
            assert calls == [True]
            assert db._conn.execute("SELECT value FROM marker").fetchall() == [
                ("keep",)
            ]
            assert db._conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            for suffix in ("", "-wal", "-shm"):
                assert mode(path.with_name(path.name + suffix)) == 0o600
    finally:
        legacy.close()


@pytest.mark.parametrize("suffix", ["-wal", "-shm"])
def test_sidecar_symlink_does_not_change_unrelated_file(tmp_path, suffix):
    path = tmp_path / "tasks.db"
    legacy = sqlite3.connect(path)
    try:
        legacy.execute("PRAGMA journal_mode=WAL")
        legacy.execute("CREATE TABLE marker (value TEXT)")
        legacy.commit()
    finally:
        legacy.close()
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_bytes(b"keep")
    unrelated.chmod(0o644)
    sidecar = path.with_name(path.name + suffix)
    sidecar.symlink_to(unrelated)
    with pytest.raises(sqlite3.OperationalError):
        TaskDB(path)
    assert sidecar.is_symlink()
    assert unrelated.read_bytes() == b"keep"
    assert mode(unrelated) == 0o644


def test_invalid_database_preserves_bytes_and_parent_permissions(tmp_path):
    tmp_path.chmod(0o755)
    path = tmp_path / "invalid.db"
    original = b"not a SQLite database\n" * 100
    path.write_bytes(original)
    path.chmod(0o644)
    with pytest.raises(sqlite3.DatabaseError):
        TaskDB(path)
    assert path.read_bytes() == original
    assert mode(tmp_path) == 0o755
    # Permission tightening occurs before opening, even if the DB is invalid.
    assert mode(path) == 0o600
