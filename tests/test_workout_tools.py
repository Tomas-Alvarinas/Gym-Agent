"""Pruebas de get_today_workout, sin depender del reloj real.

Se parchea tools.workout_tools.today_in_argentina (el nombre importado
en ese módulo) para fijar qué día es "hoy" en cada test -- mismo patrón
que ya usa el proyecto para aislar SQLite (patch de data.db.DB_PATH).
get_today_workout no necesita ningún cambio de API para ser testeable.
"""
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


def _invoke_with_fixed_today(fixed_date: date) -> str:
    from tools.workout_tools import get_today_workout

    with patch("tools.workout_tools.today_in_argentina", return_value=fixed_date):
        return get_today_workout.invoke({})


def test_get_today_workout_on_a_training_day():
    # 2026-09-21 es lunes -> "Pecho y triceps" en la rutina fixture.
    result = _invoke_with_fixed_today(date(2026, 9, 21))
    assert "Pecho y triceps" in result
    assert "Press banca" in result


def test_get_today_workout_on_a_rest_day():
    # 2026-09-19 es sabado -> dia de descanso en la rutina fixture.
    result = _invoke_with_fixed_today(date(2026, 9, 19))
    assert "descanso" in result


def test_get_today_workout_changes_with_injected_date_not_real_clock():
    # Mismo llamado, distinta fecha inyectada -> distinto resultado.
    # Prueba que la tool realmente delega en today_in_argentina() en
    # vez de usar datetime.now() por su cuenta.
    monday = _invoke_with_fixed_today(date(2026, 9, 21))
    saturday = _invoke_with_fixed_today(date(2026, 9, 19))
    assert monday != saturday


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
