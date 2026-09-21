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


def test_log_exercise_without_date_uses_argentina_today():
    # Fecha fija e inyectada (no el reloj real): parchea el nombre
    # importado en tools.exercise_tools, igual que el resto del
    # proyecto parchea data.db.DB_PATH para aislar SQLite. log_exercise
    # no necesita ningun cambio de API para ser testeable asi.
    from datetime import date as date_cls
    from unittest.mock import patch

    from tools.exercise_tools import get_exercise_history, log_exercise

    fixed_today = date_cls(2030, 6, 15)
    with patch("tools.exercise_tools.today_in_argentina", return_value=fixed_today):
        result = log_exercise.invoke({"exercise": "Remo sin fecha", "sets": [{"reps": 10}]})
    assert "(2030-06-15)" in result

    history = get_exercise_history.invoke({"exercise": "Remo sin fecha"})
    assert "session_id=" in history
    assert "] 2030-06-15:" in history


def test_log_exercise_without_date_delegates_to_today_in_argentina_not_real_clock():
    # Dos fechas inyectadas distintas -> dos resultados distintos, sin
    # importar que dia sea realmente cuando corre el test.
    from datetime import date as date_cls
    from unittest.mock import patch

    from tools.exercise_tools import log_exercise

    with patch("tools.exercise_tools.today_in_argentina", return_value=date_cls(2031, 1, 1)):
        result_a = log_exercise.invoke({"exercise": "Remo delega A", "sets": [{"reps": 10}]})
    with patch("tools.exercise_tools.today_in_argentina", return_value=date_cls(2031, 1, 2)):
        result_b = log_exercise.invoke({"exercise": "Remo delega B", "sets": [{"reps": 10}]})

    assert "(2031-01-01)" in result_a
    assert "(2031-01-02)" in result_b


def test_log_exercise_with_explicit_valid_date():
    from tools.exercise_tools import get_exercise_history, log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Sentadilla con fecha",
            "sets": [{"reps": 10, "weight_kg": 80}],
            "date": "2026-01-15",
        }
    )
    assert "Registrado: Sentadilla con fecha (2026-01-15)" in result

    history = get_exercise_history.invoke({"exercise": "Sentadilla con fecha"})
    assert "session_id=" in history
    assert "] 2026-01-15: 80.0 kg, 10 reps" in history


def test_log_exercise_with_invalid_date_is_rejected():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Sentadilla",
            "sets": [{"reps": 10}],
            "date": "15/01/2026",
        }
    )
    assert "No se pudo registrar" in result
    assert "date" in result


def test_log_exercise_with_semantically_invalid_date_is_rejected():
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Sentadilla",
            "sets": [{"reps": 10}],
            "date": "2026-13-40",
        }
    )
    assert "No se pudo registrar" in result
    assert "date" in result


def test_log_exercise_with_non_dashed_iso_date_is_rejected():
    # date.fromisoformat en Python 3.11+ acepta variantes ISO como
    # "20260115" o fechas de semana; el contrato de esta tool exige
    # YYYY-MM-DD estricto, sin ambiguedad.
    from tools.exercise_tools import log_exercise

    result = log_exercise.invoke(
        {
            "exercise": "Sentadilla",
            "sets": [{"reps": 10}],
            "date": "20260115",
        }
    )
    assert "No se pudo registrar" in result
    assert "date" in result


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


def _get_latest_session_id(exercise: str) -> int:
    """Ayuda de test: obtiene el session_id mas reciente de un ejercicio
    directamente de la capa de datos (no parseando el texto de la tool).
    """
    from data.exercise_logs import fetch_exercise_history

    sessions = fetch_exercise_history(exercise)
    return sessions[0]["session_id"]


# --- update_exercise_session ------------------------------------------------


def test_update_exercise_session_updates_weight_and_reps():
    from tools.exercise_tools import get_exercise_history, log_exercise, update_exercise_session

    log_exercise.invoke({"exercise": "Press banca update", "sets": [{"reps": 8, "weight_kg": 80}]})
    session_id = _get_latest_session_id("Press banca update")

    result = update_exercise_session.invoke(
        {"session_id": session_id, "sets": [{"reps": 5, "weight_kg": 100}]}
    )
    assert "actualizada" in result
    assert str(session_id) in result

    history = get_exercise_history.invoke({"exercise": "Press banca update"})
    assert "100.0 kg, 5 reps" in history
    assert "80.0 kg, 8 reps" not in history


def test_update_exercise_session_updates_date():
    from tools.exercise_tools import get_exercise_history, log_exercise, update_exercise_session

    log_exercise.invoke(
        {"exercise": "Remo update fecha", "sets": [{"reps": 10}], "date": "2026-01-01"}
    )
    session_id = _get_latest_session_id("Remo update fecha")

    result = update_exercise_session.invoke({"session_id": session_id, "date": "2026-02-02"})
    assert "actualizada" in result

    history = get_exercise_history.invoke({"exercise": "Remo update fecha"})
    assert "2026-02-02" in history
    assert "2026-01-01" not in history


def test_update_exercise_session_preserves_unspecified_fields():
    from tools.exercise_tools import get_exercise_history, log_exercise, update_exercise_session

    log_exercise.invoke(
        {
            "exercise": "Curl update parcial",
            "sets": [{"reps": 10, "weight_kg": 12}],
            "date": "2026-03-03",
        }
    )
    session_id = _get_latest_session_id("Curl update parcial")

    # Solo se actualiza exercise; date y sets no deberian cambiar.
    result = update_exercise_session.invoke(
        {"session_id": session_id, "exercise": "Curl update parcial renombrado"}
    )
    assert "actualizada" in result

    history_old_name = get_exercise_history.invoke({"exercise": "Curl update parcial"})
    assert "No hay registros" in history_old_name

    history_new_name = get_exercise_history.invoke(
        {"exercise": "Curl update parcial renombrado"}
    )
    assert "2026-03-03" in history_new_name
    assert "12.0 kg, 10 reps" in history_new_name


def test_update_exercise_session_preserves_exact_estimated_unknown_states():
    from tools.exercise_tools import get_exercise_history, log_exercise, update_exercise_session

    log_exercise.invoke(
        {
            "exercise": "Sentadilla update estados",
            "sets": [
                {"reps": 10, "weight_kg": 80},
                {
                    "reps": 8,
                    "reps_is_estimated": True,
                    "weight_kg": 85,
                    "weight_is_estimated": True,
                },
                {"reps": None, "weight_kg": None},
            ],
        }
    )
    session_id = _get_latest_session_id("Sentadilla update estados")

    # Se actualiza solo la fecha; los sets y sus estados no deberian tocarse.
    update_exercise_session.invoke({"session_id": session_id, "date": "2026-04-04"})

    history = get_exercise_history.invoke({"exercise": "Sentadilla update estados"})
    assert "80.0 kg, 10 reps" in history
    assert "~85.0 kg, ~8 reps" in history
    assert "peso desconocido, reps desconocidas" in history


def test_update_exercise_session_nonexistent_id_does_not_modify_data():
    from tools.exercise_tools import get_exercise_history, update_exercise_session

    result = update_exercise_session.invoke({"session_id": 999999, "exercise": "No existe"})
    assert "No se pudo actualizar" in result
    assert "999999" in result

    history = get_exercise_history.invoke({"exercise": "No existe"})
    assert "No hay registros" in history


def test_update_exercise_session_invalid_date_does_not_modify_data():
    from tools.exercise_tools import get_exercise_history, log_exercise, update_exercise_session

    log_exercise.invoke(
        {
            "exercise": "Peso muerto update invalido",
            "sets": [{"reps": 5, "weight_kg": 100}],
            "date": "2026-05-05",
        }
    )
    session_id = _get_latest_session_id("Peso muerto update invalido")

    result = update_exercise_session.invoke({"session_id": session_id, "date": "31/05/2026"})
    assert "No se pudo actualizar" in result

    history = get_exercise_history.invoke({"exercise": "Peso muerto update invalido"})
    assert "2026-05-05" in history  # sin cambios
    assert "100.0 kg, 5 reps" in history  # sets sin cambios


def test_update_exercise_session_invalid_sets_does_not_partially_modify():
    from tools.exercise_tools import get_exercise_history, log_exercise, update_exercise_session

    log_exercise.invoke(
        {"exercise": "Fondos update invalido", "sets": [{"reps": 10, "weight_kg": 0}]}
    )
    session_id = _get_latest_session_id("Fondos update invalido")

    result = update_exercise_session.invoke(
        {
            "session_id": session_id,
            "sets": [{"reps": 10, "weight_kg": 5}, {"reps": 0, "weight_kg": 5}],
        }
    )
    assert "No se pudo actualizar" in result
    assert "serie 2" in result

    history = get_exercise_history.invoke({"exercise": "Fondos update invalido"})
    # La sesion debe conservar exactamente su unica serie original, no las
    # nuevas ni una mezcla parcial.
    assert history.count("reps") == 1
    assert "0.0 kg, 10 reps" in history


# --- delete_exercise_session --------------------------------------------------


def test_delete_exercise_session_removes_session():
    from tools.exercise_tools import delete_exercise_session, get_exercise_history, log_exercise

    log_exercise.invoke({"exercise": "Plancha delete", "sets": [{"reps": 30}]})
    session_id = _get_latest_session_id("Plancha delete")

    result = delete_exercise_session.invoke({"session_id": session_id})
    assert "eliminada" in result
    assert str(session_id) in result

    history = get_exercise_history.invoke({"exercise": "Plancha delete"})
    assert "No hay registros" in history


def test_delete_exercise_session_removes_associated_sets():
    from data.db import get_connection
    from tools.exercise_tools import delete_exercise_session, log_exercise

    log_exercise.invoke(
        {"exercise": "Remo delete sets", "sets": [{"reps": 10}, {"reps": 8}, {"reps": 6}]}
    )
    session_id = _get_latest_session_id("Remo delete sets")

    delete_exercise_session.invoke({"session_id": session_id})

    conn = get_connection()
    try:
        remaining = conn.execute(
            "SELECT COUNT(*) AS n FROM exercise_sets WHERE session_id = ?",
            (session_id,),
        ).fetchone()["n"]
    finally:
        conn.close()
    assert remaining == 0


def test_delete_exercise_session_does_not_affect_other_sessions():
    from tools.exercise_tools import delete_exercise_session, get_exercise_history, log_exercise

    log_exercise.invoke(
        {"exercise": "Dominadas delete", "sets": [{"reps": 6}], "date": "2026-06-01"}
    )
    session_id_to_delete = _get_latest_session_id("Dominadas delete")
    log_exercise.invoke(
        {"exercise": "Dominadas delete", "sets": [{"reps": 8}], "date": "2026-06-02"}
    )
    session_id_to_keep = _get_latest_session_id("Dominadas delete")

    delete_exercise_session.invoke({"session_id": session_id_to_delete})

    history = get_exercise_history.invoke({"exercise": "Dominadas delete"})
    assert "2026-06-02" in history
    assert "2026-06-01" not in history
    assert str(session_id_to_keep) in history


def test_delete_exercise_session_nonexistent_id_does_not_modify_data():
    from tools.exercise_tools import delete_exercise_session, get_exercise_history, log_exercise

    log_exercise.invoke({"exercise": "Zancadas delete inexistente", "sets": [{"reps": 12}]})

    result = delete_exercise_session.invoke({"session_id": 999999})
    assert "No se pudo eliminar" in result
    assert "999999" in result

    history = get_exercise_history.invoke({"exercise": "Zancadas delete inexistente"})
    assert "12 reps" in history


# --- historial expone session_id utilizable --------------------------------


def test_get_exercise_history_exposes_usable_session_id():
    import re

    from tools.exercise_tools import (
        delete_exercise_session,
        get_exercise_history,
        log_exercise,
        update_exercise_session,
    )

    log_exercise.invoke({"exercise": "Jalon historial id", "sets": [{"reps": 10, "weight_kg": 40}]})
    history = get_exercise_history.invoke({"exercise": "Jalon historial id"})

    match = re.search(r"session_id=(\d+)", history)
    assert match is not None, "get_exercise_history debe exponer un session_id identificable"
    session_id = int(match.group(1))

    update_result = update_exercise_session.invoke(
        {"session_id": session_id, "date": "2026-07-07"}
    )
    assert "actualizada" in update_result

    delete_result = delete_exercise_session.invoke({"session_id": session_id})
    assert "eliminada" in delete_result


if __name__ == "__main__":
    # Delega en pytest para que la fixture autouse se aplique igual que
    # al correr `python -m pytest`: mismo aislamiento, mismo resultado.
    raise SystemExit(pytest.main([__file__, "-v"]))
