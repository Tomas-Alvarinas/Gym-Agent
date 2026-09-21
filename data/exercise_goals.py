"""Acceso a datos de exercise_goals. Único módulo con SQL directo de este dominio.

Las tools no arman queries: llaman a estas funciones con tipos simples
de Python (str/float/int/bool) y reciben tipos simples de vuelta.
exercise_goals es independiente de exercise_sessions/exercise_sets --
sin FK entre ambas, el objetivo y el historial son conceptos distintos.
"""
from pathlib import Path

from data.db import get_connection


def _row_to_goal(row) -> dict:
    return {
        "id": row["id"],
        "exercise": row["exercise"],
        "target_weight_kg": row["target_weight_kg"],
        "target_reps": row["target_reps"],
        "target_date": row["target_date"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
    }


def insert_exercise_goal(
    exercise: str,
    target_weight_kg: float,
    target_reps: int,
    target_date: str | None,
    created_at: str,
    db_path: Path | None = None,
) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO exercise_goals "
            "(exercise, target_weight_kg, target_reps, target_date, is_active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            (exercise, target_weight_kg, target_reps, target_date, created_at),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def fetch_exercise_goals(active_only: bool = True, db_path: Path | None = None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        query = "SELECT * FROM exercise_goals"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY created_at DESC, id DESC"
        rows = conn.execute(query).fetchall()
        return [_row_to_goal(row) for row in rows]
    finally:
        conn.close()


def fetch_exercise_goal_by_id(goal_id: int, db_path: Path | None = None) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM exercise_goals WHERE id = ?", (goal_id,)
        ).fetchone()
        return _row_to_goal(row) if row is not None else None
    finally:
        conn.close()


def fetch_active_goal_by_exercise(
    exercise: str, db_path: Path | None = None
) -> dict | None:
    """Devuelve el objetivo activo de 'exercise' (case-insensitive) o None."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM exercise_goals WHERE exercise = ? COLLATE NOCASE AND is_active = 1",
            (exercise,),
        ).fetchone()
        return _row_to_goal(row) if row is not None else None
    finally:
        conn.close()


def update_exercise_goal_record(
    goal_id: int,
    exercise: str,
    target_weight_kg: float,
    target_reps: int,
    target_date: str | None,
    is_active: bool,
    db_path: Path | None = None,
) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE exercise_goals SET exercise = ?, target_weight_kg = ?, "
            "target_reps = ?, target_date = ?, is_active = ? WHERE id = ?",
            (exercise, target_weight_kg, target_reps, target_date, int(is_active), goal_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_exercise_goal_record(goal_id: int, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("DELETE FROM exercise_goals WHERE id = ?", (goal_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
