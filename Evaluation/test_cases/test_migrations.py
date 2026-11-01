import pytest
from sqlalchemy import create_engine, text

from Backend.migration_runner import apply_sql_migrations


def test_sql_migrations_apply_once_and_record_checksum(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_create_probe.sql").write_text(
        "CREATE TABLE migration_probe (id INTEGER PRIMARY KEY);",
        encoding="utf-8",
    )
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        assert apply_sql_migrations(connection, migrations) == [
            "001_create_probe"
        ]
    with engine.begin() as connection:
        assert apply_sql_migrations(connection, migrations) == []
        rows = connection.execute(
            text("SELECT version, checksum FROM schema_migrations")
        ).all()

    assert rows[0][0] == "001_create_probe"
    assert len(rows[0][1]) == 64


def test_applied_migration_cannot_be_edited(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    migration = migrations / "001_create_probe.sql"
    migration.write_text(
        "CREATE TABLE migration_probe (id INTEGER PRIMARY KEY);",
        encoding="utf-8",
    )
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        apply_sql_migrations(connection, migrations)

    migration.write_text(
        "CREATE TABLE migration_probe (id INTEGER PRIMARY KEY, name TEXT);",
        encoding="utf-8",
    )
    with engine.begin() as connection:
        with pytest.raises(RuntimeError, match="was modified"):
            apply_sql_migrations(connection, migrations)
