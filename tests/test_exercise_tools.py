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


def test_log_exercise_valid():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {"exercise": "Press banca", "sets": 3, "reps": 8, "weight_kg": 80.0}
    )
    assert "Registrado" in result
    assert "Press banca" in result
    assert "3x8" in result
    assert "80.0 kg" in result


def test_log_exercise_missing_name():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke({"exercise": "", "sets": 3, "reps": 8})
    assert "No se pudo registrar" in result


def test_log_exercise_invalid_sets():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke({"exercise": "Sentadilla", "sets": 0, "reps": 8})
    assert "No se pudo registrar" in result
    assert "sets" in result


def test_log_exercise_negative_weight():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {"exercise": "Sentadilla", "sets": 3, "reps": 8, "weight_kg": -5}
    )
    assert "No se pudo registrar" in result
    assert "weight_kg" in result


def test_log_exercise_without_weight():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke({"exercise": "Dominadas", "sets": 4, "reps": 6})
    assert "Registrado" in result
    assert "kg" not in result


def test_get_exercise_history_empty():
    from tools.exercise_tools import get_exercise_history

    result = get_exercise_history.invoke({"exercise": "Peso muerto"})
    assert "No hay registros" in result


def test_get_exercise_history_after_logging():
    from tools.exercise_tools import get_exercise_history, log_exercise

    log_exercise.invoke({"exercise": "Remo", "sets": 4, "reps": 10, "weight_kg": 50})
    result = get_exercise_history.invoke({"exercise": "Remo"})
    assert "Historial de Remo" in result
    assert "4x10" in result
    assert "50" in result


def test_get_exercise_history_is_case_insensitive():
    from tools.exercise_tools import get_exercise_history, log_exercise

    log_exercise.invoke({"exercise": "Press militar", "sets": 3, "reps": 6})
    result = get_exercise_history.invoke({"exercise": "press militar"})
    assert "3x6" in result


if __name__ == "__main__":
    tests = [
        test_log_exercise_valid,
        test_log_exercise_missing_name,
        test_log_exercise_invalid_sets,
        test_log_exercise_negative_weight,
        test_log_exercise_without_weight,
        test_get_exercise_history_empty,
        test_get_exercise_history_after_logging,
        test_get_exercise_history_is_case_insensitive,
    ]
    for t in tests:
        _with_temp_db(t)
        print(f"OK: {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} pruebas de exercise_tools pasaron correctamente.")
