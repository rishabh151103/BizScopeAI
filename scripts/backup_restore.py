"""Create and restore a coordinated local BizScopeAI backup.

Stop the API and Streamlit processes before running either operation so the
PostgreSQL database and uploaded CSV snapshot stay consistent.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import io
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
BACKUP_MAGIC = b"BIZSCOPE-DPAPI-V1\n"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(data: bytes, *, protect: bool) -> bytes:
    """Encrypt/decrypt backup bytes for the current Windows account."""
    if os.name != "nt":
        raise RuntimeError("Encrypted local backups currently require Windows DPAPI.")
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    input_buffer = ctypes.create_string_buffer(data, len(data))
    input_blob = _DataBlob(
        len(data), ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_ubyte))
    )
    output_blob = _DataBlob()
    function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if protect:
        ok = function(
            ctypes.byref(input_blob), None, None, None, None, 1,
            ctypes.byref(output_blob),
        )
    else:
        ok = function(
            ctypes.byref(input_blob), None, None, None, None, 1,
            ctypes.byref(output_blob),
        )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _database_connection() -> tuple[list[str], dict[str, str], str]:
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("Set DATABASE_URL in .env or the environment first.")
    url = make_url(value)
    if url.get_backend_name() != "postgresql":
        raise RuntimeError("Backups require the configured PostgreSQL database.")
    args = ["--host", url.host or "127.0.0.1", "--username", url.username or ""]
    if url.port:
        args += ["--port", str(url.port)]
    if url.database:
        args += ["--dbname", url.database]
    for key in ("sslmode", "connect_timeout"):
        if key in url.query:
            args += [f"--{key.replace('_', '-')}", str(url.query[key])]
    env = os.environ.copy()
    if url.password:
        env["PGPASSWORD"] = url.password
    return args, env, url.database or ""


def _storage_paths() -> tuple[Path, Path]:
    upload_path = Path(os.getenv(
        "BIZSCOPE_DATA_DIR", str(ROOT / "dataset" / "uploads")
    )).expanduser().resolve()
    history_path = Path(os.getenv(
        "BIZSCOPE_HISTORY_DB", str(ROOT / "frontend" / "bizscope_chat_history.sqlite3")
    )).expanduser().resolve()
    return upload_path, history_path


def create_backup(destination: Path) -> None:
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Backup destination already exists: {destination}")
    connection_args, env, _ = _database_connection()
    upload_path, history_path = _storage_paths()

    dump_result = subprocess.run(
        ["pg_dump", "--format=custom", "--no-owner", *connection_args],
        check=True,
        capture_output=True,
        env=env,
    )
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("database.dump", dump_result.stdout)
        if upload_path.exists():
            for path in upload_path.rglob("*"):
                if path.is_file() and not path.is_symlink():
                    archive.write(path, (Path("uploads") / path.relative_to(upload_path)).as_posix())
        if history_path.is_file():
            archive.write(history_path, "chat_history.sqlite3")
        archive.writestr("BACKUP_FORMAT", "BizScopeAI local backup v1\n")
        archive.writestr("metadata/upload_path.txt", str(upload_path))
        archive.writestr("metadata/history_path.txt", str(history_path))
    encrypted = BACKUP_MAGIC + _dpapi(archive_bytes.getvalue(), protect=True)
    with destination.open("xb") as backup_file:
        backup_file.write(encrypted)
    print(f"Backup created: {destination}")


def restore_backup(source: Path, *, confirm: bool) -> None:
    source = source.expanduser().resolve()
    connection_args, env, database = _database_connection()
    upload_target, history_target = _storage_paths()
    if not source.is_file():
        raise FileNotFoundError(f"Backup not found: {source}")
    if upload_target.exists() and any(upload_target.iterdir()):
        raise RuntimeError("Upload destination must be empty to avoid overwriting files.")
    if history_target.exists():
        raise RuntimeError("Chat history file already exists; move it before restoring.")
    if not confirm:
        raise RuntimeError("Restore requires --confirm-database " + database)

    backup_data = source.read_bytes()
    if not backup_data.startswith(BACKUP_MAGIC):
        raise RuntimeError("Backup is not DPAPI-encrypted or uses an unsupported format.")
    plaintext = _dpapi(backup_data[len(BACKUP_MAGIC):], protect=False)
    with zipfile.ZipFile(io.BytesIO(plaintext)) as archive:
        names = archive.namelist()
        if "BACKUP_FORMAT" not in names or "database.dump" not in names:
            raise RuntimeError("This file is not a supported BizScopeAI backup.")
        for name in names:
            path = PurePosixPath(name)
            windows_path = PureWindowsPath(name)
            if (path.is_absolute() or windows_path.is_absolute()
                    or windows_path.drive or ".." in path.parts
                    or ".." in windows_path.parts):
                raise RuntimeError("Backup contains an unsafe file path.")
        expected_upload = archive.read("metadata/upload_path.txt").decode("utf-8")
        expected_history = archive.read("metadata/history_path.txt").decode("utf-8")
        if expected_upload != str(upload_target) or expected_history != str(history_target):
            raise RuntimeError(
                "This backup belongs to different data paths. Restore using the original "
                "BIZSCOPE_DATA_DIR and BIZSCOPE_HISTORY_DB settings."
            )
        with tempfile.TemporaryDirectory(prefix="bizscope-restore-") as work:
            extracted = Path(work)
            archive.extractall(extracted)
            subprocess.run(
                ["pg_restore", "--clean", "--if-exists", "--no-owner", "--exit-on-error",
                 "--dbname", " ".join([]), *connection_args],
                check=True,
                env=env,
            )
            restored_uploads = extracted / "uploads"
            history_backup = extracted / "chat_history.sqlite3"
            subprocess.run(
                ["pg_restore", "--clean", "--if-exists", "--no-owner", "--exit-on-error",
                 *connection_args, str(extracted / "database.dump")],
                check=True,
                env=env,
            )
            if restored_uploads.exists():
                upload_target.mkdir(parents=True, exist_ok=True)
                shutil.copytree(restored_uploads, upload_target, dirs_exist_ok=True)
            if history_backup.exists():
                history_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(history_backup, history_target)
    print(f"Backup restored to database {database} and {upload_target}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup", help="Create a zip backup")
    backup.add_argument("destination", type=Path)
    restore = commands.add_parser("restore", help="Replace the configured database")
    restore.add_argument("source", type=Path)
    restore.add_argument("--confirm-database", help="Type the target database name")
    options = parser.parse_args()
    if options.command == "backup":
        create_backup(options.destination)
    else:
        restore_backup(options.source,
                       confirm=options.confirm_database == _database_connection()[2])


if __name__ == "__main__":
    main()
