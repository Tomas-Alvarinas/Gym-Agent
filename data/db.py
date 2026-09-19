"""Conexión y schema de SQLite.

Único archivo que sabe dónde vive la base de datos y qué tablas existen.
No contiene lógica de negocio ni queries de dominio: eso vive en los
módulos de acceso a datos específicos (ej. data/exercise_logs.py).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "gym_agent.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS exercise_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise TEXT NOT NULL,
    date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exercise_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES exercise_sessions(id) ON DELETE CASCADE,
    set_order INTEGER NOT NULL,
    reps INTEGER NOT NULL,
    weight_kg REAL
);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    return conn
