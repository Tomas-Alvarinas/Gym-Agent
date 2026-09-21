"""Acceso a datos de reminders. Único módulo con SQL directo de este dominio.

Las tools no arman queries ni conocen el detalle de almacenamiento de
weekdays (CSV en la fila): llaman a estas funciones con tipos simples
de Python (str/list[int]/bool) y reciben tipos simples de vuelta.
"""
from pathlib import Path

from data.db import get_connection


def _weekdays_to_csv(weekdays: list[int] | None) -> str | None:
    if weekdays is None:
        return None
    return ",".join(str(d) for d in weekdays)


def _csv_to_weekdays(csv: str | None) -> list[int] | None:
    if csv is None:
        return None
    return [int(d) for d in csv.split(",")]


def _row_to_reminder(row) -> dict:
    return {
        "id": row["id"],
        "message": row["message"],
        "category": row["category"],
        "time": row["time"],
        "recurrence_type": row["recurrence_type"],
        "weekdays": _csv_to_weekdays(row["weekdays"]),
        "timezone": row["timezone"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
    }


def insert_reminder(
    message: str,
    category: str | None,
    time: str,
    recurrence_type: str,
    weekdays: list[int] | None,
    timezone: str,
    created_at: str,
    db_path: Path | None = None,
) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO reminders "
            "(message, category, time, recurrence_type, weekdays, timezone, is_active, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
            (
                message,
                category,
                time,
                recurrence_type,
                _weekdays_to_csv(weekdays),
                timezone,
                created_at,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def fetch_reminders(active_only: bool = True, db_path: Path | None = None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        query = "SELECT * FROM reminders"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY created_at DESC, id DESC"
        rows = conn.execute(query).fetchall()
        return [_row_to_reminder(row) for row in rows]
    finally:
        conn.close()


def fetch_reminder_by_id(reminder_id: int, db_path: Path | None = None) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
        ).fetchone()
        return _row_to_reminder(row) if row is not None else None
    finally:
        conn.close()


def update_reminder_record(
    reminder_id: int,
    message: str,
    category: str | None,
    time: str,
    recurrence_type: str,
    weekdays: list[int] | None,
    timezone: str,
    is_active: bool,
    db_path: Path | None = None,
) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE reminders SET message = ?, category = ?, time = ?, "
            "recurrence_type = ?, weekdays = ?, timezone = ?, is_active = ? "
            "WHERE id = ?",
            (
                message,
                category,
                time,
                recurrence_type,
                _weekdays_to_csv(weekdays),
                timezone,
                int(is_active),
                reminder_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_reminder_record(reminder_id: int, db_path: Path | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
