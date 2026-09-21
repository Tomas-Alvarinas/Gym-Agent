"""Prueba de la migración idempotente que agrega reminders.last_triggered_at
a una DB creada por una versión anterior (V3.1, antes de que esa columna
existiera). Usa un archivo SQLite temporal propio -- nunca toca
data/gym_agent.db.
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

# Schema literal de V3.1: reminders tal como la creaba data/db.py antes
# de agregar last_triggered_at. No se reutiliza el _SCHEMA actual a
# propósito, para simular fielmente una DB vieja real, no la de hoy.
_V3_1_SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    category TEXT,
    time TEXT NOT NULL,
    recurrence_type TEXT NOT NULL,
    weekdays TEXT,
    timezone TEXT NOT NULL DEFAULT 'America/Argentina/Buenos_Aires',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
"""


def _make_v3_1_db_with_existing_reminder(db_path: Path) -> int:
    """Crea un archivo SQLite con el schema viejo (sin last_triggered_at)
    y un reminder insertado directamente, simulando datos reales
    preexistentes de un usuario. Devuelve el id del reminder insertado.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_V3_1_SCHEMA)
        cursor = conn.execute(
            "INSERT INTO reminders "
            "(message, category, time, recurrence_type, weekdays, timezone, is_active, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "probar la alarma de Telegram",
                None,
                "19:24",
                "daily",
                None,
                "America/Argentina/Buenos_Aires",
                1,
                "2026-09-20T10:00:00-03:00",
            ),
        )
        conn.commit()
        reminder_id = cursor.lastrowid
    finally:
        conn.close()
    return reminder_id


def test_migration_adds_column_preserves_data_and_is_idempotent():
    from data.db import get_connection

    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "v3_1_legacy.db"
        reminder_id = _make_v3_1_db_with_existing_reminder(db_path)

        # Confirmamos el punto de partida: la DB "vieja" todavia no
        # tiene la columna, tal como la tendria un usuario real de V3.1.
        raw_conn = sqlite3.connect(db_path)
        columns_before = {row[1] for row in raw_conn.execute("PRAGMA table_info(reminders)")}
        raw_conn.close()
        assert "last_triggered_at" not in columns_before

        # Mecanismo normal de inicializacion/migracion: el mismo que usa
        # toda la app en cada conexion.
        conn = get_connection(db_path)
        try:
            columns_after = {row["name"] for row in conn.execute("PRAGMA table_info(reminders)")}
            assert "last_triggered_at" in columns_after

            row = conn.execute(
                "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
            ).fetchone()
            assert row is not None
            assert row["message"] == "probar la alarma de Telegram"
            assert row["time"] == "19:24"
            assert row["recurrence_type"] == "daily"
            assert row["weekdays"] is None
            assert row["timezone"] == "America/Argentina/Buenos_Aires"
            assert bool(row["is_active"]) is True
            assert row["created_at"] == "2026-09-20T10:00:00-03:00"
            assert row["last_triggered_at"] is None
        finally:
            conn.close()

        # Idempotencia: reabrir la conexion (misma DB, ya migrada) no
        # debe fallar ni duplicar/alterar nada.
        conn2 = get_connection(db_path)
        try:
            columns_again = {row["name"] for row in conn2.execute("PRAGMA table_info(reminders)")}
            assert "last_triggered_at" in columns_again

            rows = conn2.execute("SELECT * FROM reminders").fetchall()
            assert len(rows) == 1
            assert rows[0]["id"] == reminder_id
            assert rows[0]["last_triggered_at"] is None
        finally:
            conn2.close()


def test_migration_is_noop_on_a_fresh_v3_2_database():
    from data.db import get_connection

    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "fresh.db"

        # Una DB nueva ya se crea con la columna incluida en _SCHEMA;
        # el paso de migracion no debe hacer nada ni fallar.
        conn = get_connection(db_path)
        try:
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(reminders)")}
            assert "last_triggered_at" in columns
        finally:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
