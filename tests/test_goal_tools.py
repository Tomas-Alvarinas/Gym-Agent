"""Pruebas aisladas de create_exercise_goal / list_exercise_goals /
update_exercise_goal / delete_exercise_goal, sin LLM.

Cada test corre contra una base SQLite temporal propia (fixture autouse
de pytest, mismo patrón que el resto de tests/): no toca
data/gym_agent.db y queda aislado del resto de los tests sin importar
el orden en que se ejecuten.
"""
import re
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


def _extract_goal_id(list_result: str) -> int:
    match = re.search(r"goal_id=(\d+)", list_result)
    assert match is not None
    return int(match.group(1))


# --- create_exercise_goal ---------------------------------------------


def test_create_exercise_goal_valid_with_target_date():
    from tools.goal_tools import create_exercise_goal

    result = create_exercise_goal.invoke(
        {
            "exercise": "Press banca",
            "target_weight_kg": 100,
            "target_reps": 8,
            "target_date": "2026-12-31",
        }
    )
    assert "Objetivo creado" in result
    assert "goal_id=" in result
    assert "Press banca: 100.0 kg x 8 reps" in result
    assert "2026-12-31" in result


def test_create_exercise_goal_valid_without_target_date():
    from tools.goal_tools import create_exercise_goal

    result = create_exercise_goal.invoke(
        {"exercise": "Sentadilla", "target_weight_kg": 120, "target_reps": 10}
    )
    assert "Objetivo creado" in result
    assert "Sentadilla: 120.0 kg x 10 reps" in result
    assert "fecha objetivo" not in result


def test_create_exercise_goal_missing_exercise():
    from tools.goal_tools import create_exercise_goal

    result = create_exercise_goal.invoke(
        {"exercise": "", "target_weight_kg": 100, "target_reps": 8}
    )
    assert "No se pudo crear" in result


def test_create_exercise_goal_zero_weight_rejected():
    from tools.goal_tools import create_exercise_goal

    result = create_exercise_goal.invoke(
        {"exercise": "Dominadas", "target_weight_kg": 0, "target_reps": 20}
    )
    assert "No se pudo crear" in result
    assert "target_weight_kg" in result


def test_create_exercise_goal_negative_weight_rejected():
    from tools.goal_tools import create_exercise_goal

    result = create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": -10, "target_reps": 8}
    )
    assert "No se pudo crear" in result
    assert "target_weight_kg" in result


def test_create_exercise_goal_zero_reps_rejected():
    from tools.goal_tools import create_exercise_goal

    result = create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 0}
    )
    assert "No se pudo crear" in result
    assert "target_reps" in result


def test_create_exercise_goal_invalid_target_date_rejected():
    from tools.goal_tools import create_exercise_goal

    result = create_exercise_goal.invoke(
        {
            "exercise": "Press banca",
            "target_weight_kg": 100,
            "target_reps": 8,
            "target_date": "31/12/2026",
        }
    )
    assert "No se pudo crear" in result
    assert "target_date" in result


def test_create_exercise_goal_duplicate_active_rejected():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 8}
    )
    result = create_exercise_goal.invoke(
        {"exercise": "press banca", "target_weight_kg": 105, "target_reps": 6}
    )
    assert "No se pudo crear" in result
    assert "ya existe un objetivo activo" in result

    # No debe haberse creado un segundo objetivo.
    listing = list_exercise_goals.invoke({})
    assert listing.count("goal_id=") == 1
    assert "100" in listing
    assert "105" not in listing


# --- list_exercise_goals -----------------------------------------------


def test_list_exercise_goals_empty():
    from tools.goal_tools import list_exercise_goals

    result = list_exercise_goals.invoke({})
    assert "No hay objetivos" in result


def test_list_exercise_goals_exposes_goal_id():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 8}
    )
    result = list_exercise_goals.invoke({})
    assert re.search(r"goal_id=\d+", result) is not None
    assert "Press banca" in result


def test_list_exercise_goals_excludes_inactive_by_default():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals, update_exercise_goal

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 8}
    )
    goal_id = _extract_goal_id(list_exercise_goals.invoke({}))
    update_exercise_goal.invoke({"goal_id": goal_id, "is_active": False})

    assert "No hay objetivos" in list_exercise_goals.invoke({})
    with_inactive = list_exercise_goals.invoke({"include_inactive": True})
    assert "Press banca" in with_inactive
    assert "[inactivo]" in with_inactive


# --- update_exercise_goal: campos generales --------------------------------


def test_update_exercise_goal_weight_and_reps_preserves_other_fields():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals, update_exercise_goal

    create_exercise_goal.invoke(
        {
            "exercise": "Press banca",
            "target_weight_kg": 100,
            "target_reps": 8,
            "target_date": "2026-12-31",
        }
    )
    goal_id = _extract_goal_id(list_exercise_goals.invoke({}))

    result = update_exercise_goal.invoke(
        {"goal_id": goal_id, "target_weight_kg": 105, "target_reps": 6}
    )
    assert "actualizado" in result
    assert "105" in result
    assert "6 reps" in result
    assert "Press banca" in result
    assert "2026-12-31" in result  # target_date no tocada, preservada


def test_update_exercise_goal_nonexistent_id_does_not_modify_data():
    from tools.goal_tools import list_exercise_goals, update_exercise_goal

    result = update_exercise_goal.invoke({"goal_id": 999999, "target_weight_kg": 100})
    assert "No se pudo actualizar" in result
    assert "999999" in result
    assert "No hay objetivos" in list_exercise_goals.invoke({})


def test_update_exercise_goal_invalid_weight_does_not_modify_data():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals, update_exercise_goal

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 8}
    )
    goal_id = _extract_goal_id(list_exercise_goals.invoke({}))

    result = update_exercise_goal.invoke({"goal_id": goal_id, "target_weight_kg": -5})
    assert "No se pudo actualizar" in result

    listing = list_exercise_goals.invoke({})
    assert "100.0 kg" in listing


def test_update_exercise_goal_rename_exercise_conflicts_with_existing_active_is_rejected():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals, update_exercise_goal

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 8}
    )
    create_exercise_goal.invoke(
        {"exercise": "Sentadilla", "target_weight_kg": 120, "target_reps": 10}
    )
    listing = list_exercise_goals.invoke({})
    sentadilla_id = int(re.search(r"goal_id=(\d+)\] Sentadilla", listing).group(1))

    result = update_exercise_goal.invoke({"goal_id": sentadilla_id, "exercise": "Press banca"})
    assert "No se pudo actualizar" in result
    assert "ya existe otro objetivo activo" in result

    # Sentadilla debe seguir intacta, sin renombrar.
    listing_after = list_exercise_goals.invoke({})
    assert "Sentadilla" in listing_after


def test_update_exercise_goal_deactivate_then_create_new_active_allowed():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals, update_exercise_goal

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 8}
    )
    goal_id = _extract_goal_id(list_exercise_goals.invoke({}))
    update_exercise_goal.invoke({"goal_id": goal_id, "is_active": False})

    result = create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 110, "target_reps": 5}
    )
    assert "Objetivo creado" in result

    active_listing = list_exercise_goals.invoke({})
    assert "110" in active_listing


def test_update_exercise_goal_reactivate_conflicting_is_rejected():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals, update_exercise_goal

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 8}
    )
    listing = list_exercise_goals.invoke({})
    old_goal_id = _extract_goal_id(listing)
    update_exercise_goal.invoke({"goal_id": old_goal_id, "is_active": False})

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 110, "target_reps": 5}
    )

    # Intentar reactivar el viejo choca con el nuevo, que sigue activo.
    result = update_exercise_goal.invoke({"goal_id": old_goal_id, "is_active": True})
    assert "No se pudo actualizar" in result
    assert "ya existe otro objetivo activo" in result


# --- update_exercise_goal: target_date (casos discutidos) ------------------


def test_update_exercise_goal_sets_target_date():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals, update_exercise_goal

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 8}
    )
    goal_id = _extract_goal_id(list_exercise_goals.invoke({}))

    result = update_exercise_goal.invoke({"goal_id": goal_id, "target_date": "2026-12-31"})
    assert "actualizado" in result
    assert "2026-12-31" in result

    listing = list_exercise_goals.invoke({})
    assert "2026-12-31" in listing


def test_update_exercise_goal_without_target_date_preserves_it():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals, update_exercise_goal

    create_exercise_goal.invoke(
        {
            "exercise": "Press banca",
            "target_weight_kg": 100,
            "target_reps": 8,
            "target_date": "2026-12-31",
        }
    )
    goal_id = _extract_goal_id(list_exercise_goals.invoke({}))

    # Actualiza otro campo, sin mencionar target_date ni clear_target_date.
    update_exercise_goal.invoke({"goal_id": goal_id, "target_weight_kg": 105})

    listing = list_exercise_goals.invoke({})
    assert "2026-12-31" in listing
    assert "105" in listing


def test_update_exercise_goal_clear_target_date_removes_it():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals, update_exercise_goal

    create_exercise_goal.invoke(
        {
            "exercise": "Press banca",
            "target_weight_kg": 100,
            "target_reps": 8,
            "target_date": "2026-12-31",
        }
    )
    goal_id = _extract_goal_id(list_exercise_goals.invoke({}))

    result = update_exercise_goal.invoke({"goal_id": goal_id, "clear_target_date": True})
    assert "actualizado" in result
    assert "2026-12-31" not in result
    assert "fecha objetivo" not in result

    listing = list_exercise_goals.invoke({})
    assert "2026-12-31" not in listing
    assert "fecha objetivo" not in listing


def test_update_exercise_goal_target_date_and_clear_together_is_rejected():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals, update_exercise_goal

    create_exercise_goal.invoke(
        {
            "exercise": "Press banca",
            "target_weight_kg": 100,
            "target_reps": 8,
            "target_date": "2026-12-31",
        }
    )
    goal_id = _extract_goal_id(list_exercise_goals.invoke({}))

    result = update_exercise_goal.invoke(
        {"goal_id": goal_id, "target_date": "2027-01-01", "clear_target_date": True}
    )
    assert "No se pudo actualizar" in result

    # No debe haber cambiado nada: sigue la fecha original.
    listing = list_exercise_goals.invoke({})
    assert "2026-12-31" in listing
    assert "2027-01-01" not in listing


def test_update_exercise_goal_clear_target_date_on_already_null_is_noop():
    from tools.goal_tools import create_exercise_goal, list_exercise_goals, update_exercise_goal

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 8}
    )
    goal_id = _extract_goal_id(list_exercise_goals.invoke({}))

    result = update_exercise_goal.invoke({"goal_id": goal_id, "clear_target_date": True})
    assert "actualizado" in result
    assert "No se pudo" not in result

    listing = list_exercise_goals.invoke({})
    assert "fecha objetivo" not in listing


# --- delete_exercise_goal -----------------------------------------------


def test_delete_exercise_goal_removes_it():
    from tools.goal_tools import create_exercise_goal, delete_exercise_goal, list_exercise_goals

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 8}
    )
    goal_id = _extract_goal_id(list_exercise_goals.invoke({}))

    result = delete_exercise_goal.invoke({"goal_id": goal_id})
    assert "eliminado" in result
    assert str(goal_id) in result
    assert "No hay objetivos" in list_exercise_goals.invoke({})


def test_delete_exercise_goal_nonexistent_id_does_not_modify_data():
    from tools.goal_tools import create_exercise_goal, delete_exercise_goal, list_exercise_goals

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 8}
    )

    result = delete_exercise_goal.invoke({"goal_id": 999999})
    assert "No se pudo eliminar" in result
    assert "999999" in result
    assert "Press banca" in list_exercise_goals.invoke({})


def test_delete_exercise_goal_does_not_affect_other_goals():
    from tools.goal_tools import create_exercise_goal, delete_exercise_goal, list_exercise_goals

    create_exercise_goal.invoke(
        {"exercise": "Press banca", "target_weight_kg": 100, "target_reps": 8}
    )
    to_delete_id = _extract_goal_id(list_exercise_goals.invoke({}))
    create_exercise_goal.invoke(
        {"exercise": "Sentadilla", "target_weight_kg": 120, "target_reps": 10}
    )

    delete_exercise_goal.invoke({"goal_id": to_delete_id})

    listing = list_exercise_goals.invoke({})
    assert "Press banca" not in listing
    assert "Sentadilla" in listing


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
