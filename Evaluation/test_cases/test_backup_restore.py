import zipfile
from io import BytesIO
from types import SimpleNamespace

import pytest

from scripts import backup_restore


def _write_backup(path, entries):
    content = BytesIO()
    with zipfile.ZipFile(content, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    path.write_bytes(backup_restore.BACKUP_MAGIC + content.getvalue())


def test_backup_packages_database_uploads_and_chat_history(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    (upload_dir / "dataset.csv").write_bytes(b"a\n1\n")
    history = tmp_path / "history.sqlite3"
    history.write_bytes(b"history")
    monkeypatch.setattr(backup_restore, "_storage_paths", lambda: (upload_dir, history))
    monkeypatch.setattr(
        backup_restore,
        "_database_connection",
        lambda: (["--dbname", "pilot"], {"PGPASSWORD": "secret"}, "pilot"),
    )
    monkeypatch.setattr(backup_restore, "_dpapi", lambda data, protect: data)

    def fake_run(args, check, env, capture_output):
        assert check is True
        assert capture_output is True
        assert env["PGPASSWORD"] == "secret"
        assert "--format=custom" in args
        return SimpleNamespace(stdout=b"database")

    monkeypatch.setattr(backup_restore.subprocess, "run", fake_run)
    destination = tmp_path / "backup.zip"
    backup_restore.create_backup(destination)

    assert destination.read_bytes().startswith(backup_restore.BACKUP_MAGIC)
    with zipfile.ZipFile(BytesIO(destination.read_bytes()[len(backup_restore.BACKUP_MAGIC):])) as archive:
        assert archive.read("database.dump") == b"database"
        assert archive.read("uploads/dataset.csv") == b"a\n1\n"
        assert archive.read("chat_history.sqlite3") == b"history"
        assert archive.read("metadata/upload_path.txt").decode() == str(upload_dir)


def test_restore_requires_database_confirmation_before_running_pg_restore(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    history = tmp_path / "history.sqlite3"
    monkeypatch.setattr(backup_restore, "_storage_paths", lambda: (upload_dir, history))
    monkeypatch.setattr(
        backup_restore,
        "_database_connection",
        lambda: (["--dbname", "pilot"], {}, "pilot"),
    )
    monkeypatch.setattr(backup_restore, "_dpapi", lambda data, protect: data)
    archive_path = tmp_path / "backup.zip"
    _write_backup(archive_path, {
        "BACKUP_FORMAT": "BizScopeAI local backup v1\n",
        "database.dump": "dump",
        "metadata/upload_path.txt": str(upload_dir),
        "metadata/history_path.txt": str(history),
    })

    def fail_if_called(*args, **kwargs):
        pytest.fail("pg_restore must not run without explicit database confirmation")

    monkeypatch.setattr(backup_restore.subprocess, "run", fail_if_called)
    with pytest.raises(RuntimeError, match="requires --confirm-database"):
        backup_restore.restore_backup(archive_path, confirm=False)


def test_restore_rejects_unsafe_archive_path(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    history = tmp_path / "history.sqlite3"
    monkeypatch.setattr(backup_restore, "_storage_paths", lambda: (upload_dir, history))
    monkeypatch.setattr(
        backup_restore,
        "_database_connection",
        lambda: (["--dbname", "pilot"], {}, "pilot"),
    )
    monkeypatch.setattr(backup_restore, "_dpapi", lambda data, protect: data)
    archive_path = tmp_path / "backup.zip"
    _write_backup(archive_path, {
        "BACKUP_FORMAT": "BizScopeAI local backup v1\n",
        "database.dump": "dump",
        "..\\outside.txt": "bad",
    })

    with pytest.raises(RuntimeError, match="unsafe file path"):
        backup_restore.restore_backup(archive_path, confirm=True)
