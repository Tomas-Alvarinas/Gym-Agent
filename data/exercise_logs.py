"""Acceso a datos de exercise_sessions/exercise_sets. Único módulo con SQL directo.

Las tools no arman queries ni conocen el modelo relacional: llaman a estas
funciones con tipos simples de Python (str/list[dict]) y reciben tipos
simples de vuelta.
"""
from pathlib import Path

from data.db import get_connection


def insert_exercise_log(
    exercise: str,
    sets: list[dict],
    date: str,
    db_path: Path | None = None,
) -> int:
    """sets: lista de {"reps": int, "weight_kg": float | None}, en orden."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO exercise_sessions (exercise, date) VALUES (?, ?)",
            (exercise, date),
        )
        session_id = cursor.lastrowid

        conn.executemany(
            "INSERT INTO exercise_sets (session_id, set_order, reps, weight_kg) "
            "VALUES (?, ?, ?, ?)",
            [
                (session_id, order, s["reps"], s.get("weight_kg"))
                for order, s in enumerate(sets, start=1)
            ],
        )
        conn.commit()
        return session_id
    finally:
        conn.close()


def fetch_exercise_history(
    exercise: str,
    limit: int | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    """Devuelve una lista de sesiones (mas reciente primero), cada una como
    {"date": str, "sets": [{"reps": int, "weight_kg": float | None}, ...]}.
    """
    conn = get_connection(db_path)
    try:
        session_query = (
            "SELECT id, date FROM exercise_sessions "
            "WHERE exercise = ? COLLATE NOCASE "
            "ORDER BY date DESC, id DESC"
        )
        params: list = [exercise]
        if limit is not None:
            session_query += " LIMIT ?"
            params.append(limit)

        sessions = conn.execute(session_query, params).fetchall()

        history = []
        for session in sessions:
            set_rows = conn.execute(
                "SELECT reps, weight_kg FROM exercise_sets "
                "WHERE session_id = ? ORDER BY set_order ASC",
                (session["id"],),
            ).fetchall()
            history.append(
                {
                    "date": session["date"],
                    "sets": [dict(row) for row in set_rows],
                }
            )
        return history
    finally:
        conn.close()
