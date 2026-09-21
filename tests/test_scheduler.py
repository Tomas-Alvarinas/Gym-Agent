"""Pruebas de scheduler.py: should_trigger/scheduled_occurrence_for_today
(puras, sin DB ni red) y run_tick (con SQLite temporal y Telegram
mockeado). Ningún test envía un mensaje real ni toca data/gym_agent.db.
"""
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from date_utils import ARGENTINA_TZ


@pytest.fixture(autouse=True)
def temp_db():
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_db_path = Path(tmp_dir) / "test_gym_agent.db"
        with patch("data.db.DB_PATH", temp_db_path):
            yield


def _daily_reminder(time="18:30", last_triggered_at=None, is_active=True):
    return {
        "id": 1,
        "message": "tomar creatina",
        "category": None,
        "time": time,
        "recurrence_type": "daily",
        "weekdays": None,
        "timezone": "America/Argentina/Buenos_Aires",
        "is_active": is_active,
        "created_at": "2026-01-01T00:00:00-03:00",
        "last_triggered_at": last_triggered_at,
    }


def _weekly_reminder(time="18:00", weekdays=None, last_triggered_at=None, is_active=True):
    return {
        "id": 2,
        "message": "ir al gimnasio",
        "category": None,
        "time": time,
        "recurrence_type": "weekly",
        "weekdays": weekdays if weekdays is not None else [0, 2, 4],
        "timezone": "America/Argentina/Buenos_Aires",
        "is_active": is_active,
        "created_at": "2026-01-01T00:00:00-03:00",
        "last_triggered_at": last_triggered_at,
    }


# 2026-09-21 es lunes (weekday()==0).
_MONDAY = 2026, 9, 21
_TUESDAY = 2026, 9, 22


def _dt(day_tuple, hour, minute, second=0):
    year, month, day = day_tuple
    return datetime(year, month, day, hour, minute, second, tzinfo=ARGENTINA_TZ)


# --- scheduled_occurrence_for_today ---------------------------------------


def test_scheduled_occurrence_for_today_daily():
    from scheduler import scheduled_occurrence_for_today

    reminder = _daily_reminder(time="18:30")
    now = _dt(_MONDAY, 10, 0)
    assert scheduled_occurrence_for_today(reminder, now) == _dt(_MONDAY, 18, 30)


def test_scheduled_occurrence_for_today_weekly_non_matching_day_is_none():
    from scheduler import scheduled_occurrence_for_today

    reminder = _weekly_reminder(time="18:00", weekdays=[1, 3])  # martes, jueves
    monday = _dt(_MONDAY, 10, 0)
    assert scheduled_occurrence_for_today(reminder, monday) is None


# --- should_trigger: ventana de horario (requisitos 1-4) -------------------


def test_1_does_not_trigger_before_scheduled_time():
    from scheduler import should_trigger

    reminder = _daily_reminder(time="18:30")
    assert should_trigger(reminder, _dt(_MONDAY, 18, 29, 59)) is False


def test_2_triggers_exactly_at_scheduled_time():
    from scheduler import should_trigger

    reminder = _daily_reminder(time="18:30")
    assert should_trigger(reminder, _dt(_MONDAY, 18, 30, 0)) is True


def test_3_triggers_within_5_minute_tolerance_window():
    from scheduler import should_trigger

    reminder = _daily_reminder(time="18:30")
    assert should_trigger(reminder, _dt(_MONDAY, 18, 34)) is True
    assert should_trigger(reminder, _dt(_MONDAY, 18, 35)) is True  # borde inclusive


def test_4_does_not_trigger_after_5_minute_tolerance_window():
    from scheduler import should_trigger

    reminder = _daily_reminder(time="18:30")
    assert should_trigger(reminder, _dt(_MONDAY, 18, 35, 1)) is False
    assert should_trigger(reminder, _dt(_MONDAY, 18, 40)) is False


# --- should_trigger: deduplicacion (requisito 5) ----------------------------


def test_5_does_not_trigger_twice_in_same_window_after_successful_send():
    from scheduler import should_trigger

    occurrence = _dt(_MONDAY, 18, 30)
    reminder = _daily_reminder(time="18:30", last_triggered_at=occurrence.isoformat())
    assert should_trigger(reminder, _dt(_MONDAY, 18, 32)) is False


# --- run_tick: Telegram falla (requisito 6) --------------------------------


def test_6_run_tick_does_not_mark_triggered_when_telegram_fails():
    from data.reminders import fetch_reminder_by_id, insert_reminder
    from scheduler import run_tick

    reminder_id = insert_reminder(
        "tomar creatina", None, "18:30", "daily", None,
        "America/Argentina/Buenos_Aires", "2026-01-01T00:00:00-03:00",
    )

    with patch("scheduler.send_telegram_message", return_value=False) as mock_send:
        triggered = run_tick(now=_dt(_MONDAY, 18, 30))

    mock_send.assert_called_once_with("Recordatorio: tomar creatina")
    assert triggered == []
    reminder = fetch_reminder_by_id(reminder_id)
    assert reminder["last_triggered_at"] is None


def test_run_tick_marks_triggered_on_successful_send():
    from data.reminders import fetch_reminder_by_id, insert_reminder
    from scheduler import run_tick

    reminder_id = insert_reminder(
        "tomar creatina", None, "18:30", "daily", None,
        "America/Argentina/Buenos_Aires", "2026-01-01T00:00:00-03:00",
    )

    now = _dt(_MONDAY, 18, 30)
    with patch("scheduler.send_telegram_message", return_value=True) as mock_send:
        triggered = run_tick(now=now)

    mock_send.assert_called_once_with("Recordatorio: tomar creatina")
    assert triggered == [reminder_id]
    reminder = fetch_reminder_by_id(reminder_id)
    assert reminder["last_triggered_at"] == now.isoformat()


def test_run_tick_second_tick_in_same_window_does_not_resend():
    from data.reminders import insert_reminder
    from scheduler import run_tick

    reminder_id = insert_reminder(
        "tomar creatina", None, "18:30", "daily", None,
        "America/Argentina/Buenos_Aires", "2026-01-01T00:00:00-03:00",
    )

    with patch("scheduler.send_telegram_message", return_value=True) as mock_send:
        first = run_tick(now=_dt(_MONDAY, 18, 30))
        second = run_tick(now=_dt(_MONDAY, 18, 32))

    assert first == [reminder_id]
    assert second == []
    assert mock_send.call_count == 1


# --- should_trigger: weekly y weekdays (requisito 7) ------------------------


def test_7_weekly_reminder_only_triggers_on_matching_weekdays():
    from scheduler import should_trigger

    reminder = _weekly_reminder(time="18:00", weekdays=[0, 2, 4])  # lun, mie, vie
    assert should_trigger(reminder, _dt(_MONDAY, 18, 0)) is True
    assert should_trigger(reminder, _dt(_TUESDAY, 18, 0)) is False


# --- should_trigger: inactivo (requisito 8) ---------------------------------


def test_8_inactive_reminder_never_triggers():
    from scheduler import should_trigger

    reminder = _daily_reminder(time="18:30", is_active=False)
    assert should_trigger(reminder, _dt(_MONDAY, 18, 30)) is False


# --- should_trigger: cambios de horario durante el dia (requisito 9) -------


def test_9_case_a_time_moved_later_same_day_triggers_again():
    from scheduler import should_trigger

    sent_at_9 = _dt(_MONDAY, 9, 0, 3)
    reminder = _daily_reminder(time="18:30", last_triggered_at=sent_at_9.isoformat())
    assert should_trigger(reminder, _dt(_MONDAY, 18, 30)) is True


def test_9_case_b_time_moved_earlier_same_day_does_not_retrigger():
    from scheduler import should_trigger

    sent_at_18 = _dt(_MONDAY, 18, 0, 5)
    reminder = _daily_reminder(time="09:00", last_triggered_at=sent_at_18.isoformat())
    assert should_trigger(reminder, _dt(_MONDAY, 9, 0)) is False


def test_9_case_c_recurrence_changed_so_today_no_longer_applies():
    from scheduler import should_trigger

    # Nunca se habia enviado, pero aunque se hubiera enviado un dia
    # anterior, scheduled_occurrence_for_today ya da None para hoy
    # antes de mirar last_triggered_at.
    reminder = _weekly_reminder(time="18:00", weekdays=[1, 3])  # martes, jueves
    assert should_trigger(reminder, _dt(_MONDAY, 18, 0)) is False


# --- helper interno de sleep -------------------------------------------


def test_seconds_until_next_minute():
    from scheduler import _seconds_until_next_minute

    now = _dt(_MONDAY, 18, 30, 45)
    assert _seconds_until_next_minute(now) == 15


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
