"""Pruebas de date_utils: now_in_argentina()/today_in_argentina(), la
fuente de verdad de "ahora"/"hoy" que usan agent/graph.py, log_exercise,
get_today_workout y reminder_tools (created_at).
"""
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from date_utils import ARGENTINA_TZ, now_in_argentina, today_in_argentina


def test_today_in_argentina_returns_a_date_without_injected_now():
    result = today_in_argentina()
    assert isinstance(result, date)


def test_today_in_argentina_uses_injected_now():
    fixed_now = datetime(2026, 9, 21, 12, 0, tzinfo=ARGENTINA_TZ)
    assert today_in_argentina(now=fixed_now) == date(2026, 9, 21)


def test_today_in_argentina_differs_from_utc_near_midnight():
    # 2026-09-22 01:00 UTC ya cambio de dia en UTC, pero en Argentina
    # (UTC-3) todavia son las 22:00 del 2026-09-21. Este es el caso
    # exacto que rompia un servidor corriendo en UTC.
    utc_instant = datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc)
    assert utc_instant.date() == date(2026, 9, 22)  # lo que veria un host en UTC
    assert today_in_argentina(now=utc_instant) == date(2026, 9, 21)  # lo correcto


def test_today_in_argentina_converts_from_any_timezone():
    # Instante fijo expresado en otro huso (Madrid, UTC+2 en septiembre):
    # 2026-09-22 03:00 Madrid == 2026-09-22 01:00 UTC == 2026-09-21 22:00 AR.
    madrid_instant = datetime(2026, 9, 22, 3, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    assert today_in_argentina(now=madrid_instant) == date(2026, 9, 21)


def test_now_in_argentina_returns_a_datetime_without_injected_now():
    result = now_in_argentina()
    assert isinstance(result, datetime)
    assert result.tzinfo is not None


def test_now_in_argentina_converts_injected_instant_to_argentina_tz():
    utc_instant = datetime(2026, 9, 22, 1, 30, tzinfo=timezone.utc)
    result = now_in_argentina(now=utc_instant)
    assert result == datetime(2026, 9, 21, 22, 30, tzinfo=ARGENTINA_TZ)
    assert result.date() == date(2026, 9, 21)


def test_today_in_argentina_is_consistent_with_now_in_argentina():
    fixed_now = datetime(2026, 9, 22, 1, 30, tzinfo=timezone.utc)
    assert today_in_argentina(now=fixed_now) == now_in_argentina(now=fixed_now).date()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
