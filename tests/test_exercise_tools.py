"""Pruebas aisladas de log_exercise / get_exercise_history, sin LLM.

Usa una base SQLite temporal (no toca data/gym_agent.db).
Ejecutar con: python tests/test_exercise_tools.py
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _with_temp_db(test_fn):
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_db_path = Path(tmp_dir) / "test_gym_agent.db"
        with patch("data.db.DB_PATH", temp_db_path):
            test_fn()


def test_log_exercise_valid_multiple_sets():
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
    assert "80.0 kg x 10" in result
    assert "85.0 kg x 8" in result
    assert "90.0 kg x 6" in result


def test_log_exercise_valid_without_weight():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Flexiones",
            "sets": [{"reps": 15}, {"reps": 12}, {"reps": 10}],
        }
    )
    assert "Registrado: Flexiones" in result
    assert "15 reps" in result
    assert "12 reps" in result
    assert "10 reps" in result
    assert "kg" not in result


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
        {
            "exercise": "Sentadilla",
            "sets": [{"reps": 10}, {"reps": 0}],
        }
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


def test_get_exercise_history_empty():
    from tools.exercise_tools import get_exercise_history

    result = get_exercise_history.invoke({"exercise": "Peso muerto"})
    assert "No hay registros" in result


def test_get_exercise_history_after_logging():
    from tools.exercise_tools import get_exercise_history, log_exercise

    log_exercise.invoke(
        {
            "exercise": "Curl de biceps",
            "sets": [
                {"weight_kg": 12, "reps": 10},
                {"weight_kg": 12, "reps": 10},
                {"weight_kg": 12, "reps": 8},
            ],
        }
    )
    result = get_exercise_history.invoke({"exercise": "Curl de biceps"})
    assert "Historial de Curl de biceps" in result
    assert "12.0 kg x 10, 12.0 kg x 10, 12.0 kg x 8" in result


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
    insert_exercise_log("Remo", [{"reps": 10, "weight_kg": 40}], "2020-01-01")
    log_exercise.invoke({"exercise": "Remo", "sets": [{"reps": 10, "weight_kg": 50}]})

    result = get_exercise_history.invoke({"exercise": "Remo"})
    lines = [line for line in result.splitlines() if line.startswith("-")]
    assert len(lines) == 2
    assert "50.0 kg" in lines[0]  # la mas reciente (hoy) va primero
    assert "2020-01-01" in lines[1]


if __name__ == "__main__":
    tests = [
        test_log_exercise_valid_multiple_sets,
        test_log_exercise_valid_without_weight,
        test_log_exercise_missing_name,
        test_log_exercise_empty_sets,
        test_log_exercise_invalid_reps_in_one_set,
        test_log_exercise_negative_weight_in_one_set,
        test_get_exercise_history_empty,
        test_get_exercise_history_after_logging,
        test_get_exercise_history_is_case_insensitive,
        test_get_exercise_history_multiple_sessions_ordered_desc,
    ]
    for t in tests:
        _with_temp_db(t)
        print(f"OK: {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} pruebas de exercise_tools pasaron correctamente.")
