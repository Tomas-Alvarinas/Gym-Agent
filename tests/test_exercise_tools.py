"""Pruebas aisladas de log_exercise / get_exercise_history, sin LLM.

Cada test corre contra una base SQLite temporal propia (fixture autouse
de pytest): no toca data/gym_agent.db y queda aislado del resto de los
tests sin importar el orden en que se ejecuten. La fixture la aplica
pytest automáticamente a cada test_* -- por eso corre igual con
`pytest` que con `python tests/test_exercise_tools.py` (ver __main__).
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def temp_db():
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_db_path = Path(tmp_dir) / "test_gym_agent.db"
        with patch("data.db.DB_PATH", temp_db_path):
            yield


def test_log_exercise_valid_exact_values():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Press banca",
            "sets": [
                {"weight_kg": 80, "reps": 10},
                {"weight_kg": 85, "reps": 8},
                {"weight_kg": 90, "reps": 6},
            ],
        }
    )
    assert "Registrado: Press banca" in result
    assert "80.0 kg, 10 reps" in result
    assert "85.0 kg, 8 reps" in result
    assert "90.0 kg, 6 reps" in result
    assert "~" not in result


def test_log_exercise_valid_without_weight():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Flexiones",
            "sets": [{"reps": 15}, {"reps": 12}, {"reps": 10}],
        }
    )
    assert "peso desconocido, 15 reps" in result
    assert "peso desconocido, 12 reps" in result
    assert "peso desconocido, 10 reps" in result


def test_log_exercise_fully_unknown_sets():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Press militar",
            "sets": [{}, {}, {}],
        }
    )
    assert "Registrado: Press militar" in result
    assert result.count("peso desconocido, reps desconocidas") == 3


def test_log_exercise_estimated_weight_and_reps():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Sentadilla",
            "sets": [
                {
                    "weight_kg": 80,
                    "weight_is_estimated": True,
                    "reps": 10,
                    "reps_is_estimated": False,
                }
            ],
        }
    )
    assert "~80.0 kg, 10 reps" in result


def test_log_exercise_mixed_estimation_across_sets():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Peso muerto",
            "sets": [
                {"weight_kg": 100, "reps": 5},
                {"weight_kg": 100, "weight_is_estimated": True, "reps": 5, "reps_is_estimated": True},
                {"reps": 4},
            ],
        }
    )
    assert "100.0 kg, 5 reps" in result
    assert "~100.0 kg, ~5 reps" in result
    assert "peso desconocido, 4 reps" in result


def test_log_exercise_missing_name():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke({"exercise": "", "sets": [{"reps": 10}]})
    assert "No se pudo registrar" in result


def test_log_exercise_empty_sets():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke({"exercise": "Sentadilla", "sets": []})
    assert "No se pudo registrar" in result
    assert "al menos una serie" in result


def test_log_exercise_invalid_reps_in_one_set():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {"exercise": "Sentadilla", "sets": [{"reps": 10}, {"reps": 0}]}
    )
    assert "No se pudo registrar" in result
    assert "serie 2" in result


def test_log_exercise_negative_weight_in_one_set():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Sentadilla",
            "sets": [{"reps": 10, "weight_kg": 60}, {"reps": 8, "weight_kg": -5}],
        }
    )
    assert "No se pudo registrar" in result
    assert "serie 2" in result


def test_log_exercise_reps_estimated_without_value_is_rejected():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Sentadilla",
            "sets": [{"reps": None, "reps_is_estimated": True}],
        }
    )
    assert "No se pudo registrar" in result
    assert "reps" in result
    assert "estimado" in result


def test_log_exercise_weight_estimated_without_value_is_rejected():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Sentadilla",
            "sets": [{"reps": 8, "weight_kg": None, "weight_is_estimated": True}],
        }
    )
    assert "No se pudo registrar" in result
    assert "weight_kg" in result
    assert "estimado" in result


def test_get_exercise_history_empty():
    from tools.exercise_tools import get_exercise_history

    result = get_exercise_history.invoke({"exercise": "Peso muerto"})
    assert "No hay registros" in result


def test_get_exercise_history_preserves_exact_estimated_unknown():
    from tools.exercise_tools import get_exercise_history, log_exercise

    log_exercise.invoke(
        {
            "exercise": "Curl de biceps",
            "sets": [
                {"weight_kg": 12, "reps": 10},
                {"weight_kg": 12, "weight_is_estimated": True, "reps": 10},
                {"reps": None, "weight_kg": None},
            ],
        }
    )
    result = get_exercise_history.invoke({"exercise": "Curl de biceps"})
    assert "12.0 kg, 10 reps" in result
    assert "~12.0 kg, 10 reps" in result
    assert "peso desconocido, reps desconocidas" in result


def test_get_exercise_history_is_case_insensitive():
    from tools.exercise_tools import get_exercise_history, log_exercise

    log_exercise.invoke({"exercise": "Press militar", "sets": [{"reps": 6}]})
    result = get_exercise_history.invoke({"exercise": "press militar"})
    assert "6 reps" in result


def test_get_exercise_history_multiple_sessions_ordered_desc():
    from tools.exercise_tools import get_exercise_history, log_exercise
    from data.exercise_logs import insert_exercise_log

    # Sesion mas vieja insertada directamente en la capa de datos para
    # simular una fecha anterior (log_exercise siempre usa "hoy").
    insert_exercise_log(
        "Remo",
        [{"reps": 10, "reps_is_estimated": False, "weight_kg": 40, "weight_is_estimated": False}],
        "2020-01-01",
    )
    log_exercise.invoke({"exercise": "Remo", "sets": [{"reps": 10, "weight_kg": 50}]})

    result = get_exercise_history.invoke({"exercise": "Remo"})
    lines = [line for line in result.splitlines() if line.startswith("-")]
    assert len(lines) == 2
    assert "50.0 kg" in lines[0]  # la mas reciente (hoy) va primero
    assert "2020-01-01" in lines[1]


if __name__ == "__main__":
    # Delega en pytest para que la fixture autouse se aplique igual que
    # al correr `python -m pytest`: mismo aislamiento, mismo resultado.
    raise SystemExit(pytest.main([__file__, "-v"]))
