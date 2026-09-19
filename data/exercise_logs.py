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
    """sets: lista de
    {"reps": int | None, "reps_is_estimated": bool,
     "weight_kg": float | None, "weight_is_estimated": bool},
    en orden.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO exercise_sessions (exercise, date) VALUES (?, ?)",
            (exercise, date),
        )
        session_id = cursor.lastrowid

        conn.executemany(
            "INSERT INTO exercise_sets "
            "(session_id, set_order, reps, reps_is_estimated, weight_kg, weight_is_estimated) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    session_id,
                    order,
                    s["reps"],
                    int(s["reps_is_estimated"]),
                    s["weight_kg"],
                    int(s["weight_is_estimated"]),
                )
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
    {"date": str, "sets": [
        {"reps": int | None, "reps_is_estimated": bool,
         "weight_kg": float | None, "weight_is_estimated": bool},
        ...
    ]}.
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
                "SELECT reps, reps_is_estimated, weight_kg, weight_is_estimated "
                "FROM exercise_sets WHERE session_id = ? ORDER BY set_order ASC",
                (session["id"],),
            ).fetchall()
            history.append(
                {
                    "date": session["date"],
                    "sets": [
                        {
                            "reps": row["reps"],
                            "reps_is_estimated": bool(row["reps_is_estimated"]),
                            "weight_kg": row["weight_kg"],
                            "weight_is_estimated": bool(row["weight_is_estimated"]),
                        }
                        for row in set_rows
                    ],
                }
            )
        return history
    finally:
        conn.close()
