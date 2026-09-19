"""Acceso a datos de exercise_logs. Único módulo con SQL directo.

Las tools no arman queries: llaman a estas funciones y reciben
tipos de Python (int/float/str/dict), no cursores ni filas crudas.
"""
from pathlib import Path

from data.db import get_connection


def insert_exercise_log(
    exercise: str,
    sets: int,
    reps: int,
    date: str,
    weight_kg: float | None = None,
    db_path: Path | None = None,
) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO exercise_logs (exercise, sets, reps, weight_kg, date) "
            "VALUES (?, ?, ?, ?, ?)",
            (exercise, sets, reps, weight_kg, date),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def fetch_exercise_history(
    exercise: str,
    limit: int | None = None,
    db_path: Path | None = None,
) -> list[dict]:
    conn = get_connection(db_path)
    try:
        query = (
            "SELECT exercise, sets, reps, weight_kg, date FROM exercise_logs "
            "WHERE exercise = ? COLLATE NOCASE "
            "ORDER BY date DESC, id DESC"
        )
        params: list = [exercise]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
