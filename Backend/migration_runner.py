"""Apply ordered SQL migrations and record their content hashes."""

from hashlib import sha256
from pathlib import Path

from sqlalchemy import text


def apply_sql_migrations(connection, migrations_dir: Path) -> list[str]:
    """Apply unapplied ``*.sql`` migrations in filename order.

    The caller owns the transaction. Editing a migration after it has been
    applied is rejected so schema history stays reproducible.
    """
    connection.execute(text(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version VARCHAR(255) PRIMARY KEY, "
        "checksum VARCHAR(64) NOT NULL, "
        "applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    ))
    recorded = dict(connection.execute(text(
        "SELECT version, checksum FROM schema_migrations"
    )).all())

    applied_now = []
    for migration_path in sorted(migrations_dir.glob("*.sql")):
        version = migration_path.stem
        sql = migration_path.read_text(encoding="utf-8")
        checksum = sha256(sql.encode("utf-8")).hexdigest()

        if version in recorded:
            if recorded[version] != checksum:
                raise RuntimeError(
                    f"Applied migration {version} was modified. "
                    "Create a new migration instead."
                )
            continue

        if not sql.strip():
            raise RuntimeError(f"Migration {version} is empty.")

        connection.exec_driver_sql(sql)
        connection.execute(
            text(
                "INSERT INTO schema_migrations (version, checksum) "
                "VALUES (:version, :checksum)"
            ),
            {"version": version, "checksum": checksum},
        )
        applied_now.append(version)

    return applied_now
