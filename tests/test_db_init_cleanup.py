import sqlite3
import pytest
from tasukura.db import TaskDB


def test_failed_initialization_closes_connection(tmp_path):
    p = tmp_path / "broken.db"
    original = b"not a sqlite database\n" * 100
    p.write_bytes(original)
    with pytest.raises(sqlite3.DatabaseError) as info:
        TaskDB(p)
    tb = info.value.__traceback__
    db = None
    while tb:
        if tb.tb_frame.f_code.co_name == "__init__":
            db = tb.tb_frame.f_locals.get("self")
        tb = tb.tb_next
    assert db is not None
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        db._conn.execute("SELECT 1")
    assert p.read_bytes() == original


@pytest.mark.parametrize(
    "cleanup_error", [RuntimeError("close failed"), KeyboardInterrupt()]
)
def test_cleanup_failure_preserves_initialization_error(
    tmp_path, monkeypatch, cleanup_error
):
    initial_error = sqlite3.OperationalError("initialization failed")
    close_attempts = []

    class FailingConnection(sqlite3.Connection):
        def execute(self, *args, **kwargs):
            raise initial_error

        def close(self):
            close_attempts.append(True)
            raise cleanup_error

    conn = sqlite3.connect(":memory:", factory=FailingConnection)
    monkeypatch.setattr(sqlite3, "connect", lambda *args, **kwargs: conn)
    try:
        with pytest.raises(sqlite3.OperationalError) as info:
            TaskDB(tmp_path / "failed.db")
        assert info.value is initial_error
        assert close_attempts == [True]
        assert any(
            type(cleanup_error).__name__ in note for note in info.value.__notes__
        )
    finally:
        sqlite3.Connection.close(conn)


def test_close_after_failure_does_not_undo_committed_schema(tmp_path, monkeypatch):
    def commit_then_fail(self):
        self._conn.execute("CREATE TABLE committed_migration (value TEXT)")
        self._conn.execute("INSERT INTO committed_migration VALUES ('kept')")
        self._conn.commit()
        raise RuntimeError("after committed migration")

    monkeypatch.setattr(TaskDB, "_run_migrations", commit_then_fail)
    path = tmp_path / "committed.db"
    with pytest.raises(RuntimeError, match="after committed migration"):
        TaskDB(path)
    conn = sqlite3.connect(path)
    try:
        assert conn.execute("SELECT value FROM committed_migration").fetchall() == [
            ("kept",)
        ]
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE name='tasks'"
        ).fetchone() == ("tasks",)
    finally:
        conn.close()
