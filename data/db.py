"""Conexión y schema de SQLite.

Único archivo que sabe dónde vive la base de datos y qué tablas existen.
No contiene lógica de negocio ni queries de dominio: eso vive en los
módulos de acceso a datos específicos (ej. data/exercise_logs.py).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "gym_agent.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS exercise_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise TEXT NOT NULL,
    sets INTEGER NOT NULL,
    reps INTEGER NOT NULL,
    weight_kg REAL,
    date TEXT NOT NULL
);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn
