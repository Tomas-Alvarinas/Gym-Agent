"""Pruebas aisladas de create_reminder / list_reminders / update_reminder /
delete_reminder, sin LLM.

Cada test corre contra una base SQLite temporal propia (fixture autouse
de pytest, mismo patrón que test_exercise_tools.py): no toca
data/gym_agent.db y queda aislado del resto de los tests sin importar
el orden en que se ejecuten.
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


# --- create_reminder ---------------------------------------------------


def test_create_reminder_daily():
    from tools.reminder_tools import create_reminder

    result = create_reminder.invoke(
        {"message": "Tomar creatina", "time": "09:00", "recurrence_type": "daily"}
    )
    assert "Recordatorio creado" in result
    assert "reminder_id=" in result
    assert "Tomar creatina" in result
    assert "09:00" in result
    assert "todos los días" in result


def test_create_reminder_weekly():
    from tools.reminder_tools import create_reminder

    result = create_reminder.invoke(
        {
            "message": "Ir al gimnasio",
            "time": "18:00",
            "recurrence_type": "weekly",
            "weekdays": [0, 2, 4],
        }
    )
    assert "Recordatorio creado" in result
    assert "lunes, miércoles, viernes" in result


def test_create_reminder_with_category():
    from tools.reminder_tools import create_reminder

    result = create_reminder.invoke(
        {
            "message": "Tomar creatina",
            "time": "09:00",
            "recurrence_type": "daily",
            "category": "suplementos",
        }
    )
    assert "(suplementos)" in result


def test_create_reminder_missing_message():
    from tools.reminder_tools import create_reminder

    result = create_reminder.invoke(
        {"message": "", "time": "09:00", "recurrence_type": "daily"}
    )
    assert "No se pudo crear" in result


def test_create_reminder_invalid_time_format():
    from tools.reminder_tools import create_reminder

    result = create_reminder.invoke(
        {"message": "Tomar creatina", "time": "9am", "recurrence_type": "daily"}
    )
    assert "No se pudo crear" in result
    assert "time" in result


def test_create_reminder_invalid_time_out_of_range():
    from tools.reminder_tools import create_reminder

    result = create_reminder.invoke(
        {"message": "Tomar creatina", "time": "25:00", "recurrence_type": "daily"}
    )
    assert "No se pudo crear" in result


def test_create_reminder_invalid_recurrence_type():
    from tools.reminder_tools import create_reminder

    result = create_reminder.invoke(
        {"message": "Tomar creatina", "time": "09:00", "recurrence_type": "monthly"}
    )
    assert "No se pudo crear" in result
    assert "recurrence_type" in result


def test_create_reminder_daily_with_weekdays_is_rejected():
    from tools.reminder_tools import create_reminder

    result = create_reminder.invoke(
        {
            "message": "Tomar creatina",
            "time": "09:00",
            "recurrence_type": "daily",
            "weekdays": [0, 2],
        }
    )
    assert "No se pudo crear" in result
    assert "weekdays" in result


def test_create_reminder_weekly_without_weekdays_is_rejected():
    from tools.reminder_tools import create_reminder

    result = create_reminder.invoke(
        {"message": "Ir al gimnasio", "time": "18:00", "recurrence_type": "weekly"}
    )
    assert "No se pudo crear" in result
    assert "weekdays" in result


def test_create_reminder_weekday_out_of_range_is_rejected():
    from tools.reminder_tools import create_reminder

    result = create_reminder.invoke(
        {
            "message": "Ir al gimnasio",
            "time": "18:00",
            "recurrence_type": "weekly",
            "weekdays": [0, 7],
        }
    )
    assert "No se pudo crear" in result
    assert "0" in result and "6" in result


def test_create_reminder_duplicate_weekdays_is_rejected():
    from tools.reminder_tools import create_reminder

    result = create_reminder.invoke(
        {
            "message": "Ir al gimnasio",
            "time": "18:00",
            "recurrence_type": "weekly",
            "weekdays": [0, 2, 0],
        }
    )
    assert "No se pudo crear" in result
    assert "duplicados" in result


# --- list_reminders ------------------------------------------------------


def test_list_reminders_empty():
    from tools.reminder_tools import list_reminders

    result = list_reminders.invoke({})
    assert "No hay recordatorios" in result


def test_list_reminders_exposes_reminder_id():
    import re

    from tools.reminder_tools import create_reminder, list_reminders

    create_reminder.invoke(
        {"message": "Tomar creatina", "time": "09:00", "recurrence_type": "daily"}
    )
    result = list_reminders.invoke({})
    assert re.search(r"reminder_id=\d+", result) is not None
    assert "Tomar creatina" in result


def test_list_reminders_excludes_inactive_by_default():
    from tools.reminder_tools import create_reminder, list_reminders, update_reminder

    create_reminder.invoke(
        {"message": "Tomar creatina", "time": "09:00", "recurrence_type": "daily"}
    )
    reminder_id = _extract_reminder_id(list_reminders.invoke({}))
    update_reminder.invoke({"reminder_id": reminder_id, "is_active": False})

    active_only = list_reminders.invoke({})
    assert "No hay recordatorios" in active_only

    with_inactive = list_reminders.invoke({"include_inactive": True})
    assert "Tomar creatina" in with_inactive
    assert "[inactivo]" in with_inactive


# --- update_reminder -------------------------------------------------------


def _extract_reminder_id(list_result: str) -> int:
    import re

    match = re.search(r"reminder_id=(\d+)", list_result)
    assert match is not None
    return int(match.group(1))


def test_update_reminder_message_preserves_other_fields():
    from tools.reminder_tools import create_reminder, list_reminders, update_reminder

    create_reminder.invoke(
        {
            "message": "Tomar creatina",
            "time": "09:00",
            "recurrence_type": "weekly",
            "weekdays": [0, 2, 4],
            "category": "suplementos",
        }
    )
    reminder_id = _extract_reminder_id(list_reminders.invoke({}))

    result = update_reminder.invoke({"reminder_id": reminder_id, "message": "Tomar creatina y proteina"})
    assert "actualizado" in result
    assert "Tomar creatina y proteina" in result
    assert "09:00" in result
    assert "(suplementos)" in result
    assert "lunes, miércoles, viernes" in result


def test_update_reminder_time_only():
    from tools.reminder_tools import create_reminder, list_reminders, update_reminder

    create_reminder.invoke(
        {"message": "Tomar creatina", "time": "09:00", "recurrence_type": "daily"}
    )
    reminder_id = _extract_reminder_id(list_reminders.invoke({}))

    result = update_reminder.invoke({"reminder_id": reminder_id, "time": "10:00"})
    assert "10:00" in result
    assert "Tomar creatina" in result


def test_update_reminder_weekly_to_daily_without_weekdays_clears_them():
    from tools.reminder_tools import create_reminder, list_reminders, update_reminder

    create_reminder.invoke(
        {
            "message": "Ir al gimnasio",
            "time": "18:00",
            "recurrence_type": "weekly",
            "weekdays": [0, 2, 4],
        }
    )
    reminder_id = _extract_reminder_id(list_reminders.invoke({}))

    result = update_reminder.invoke({"reminder_id": reminder_id, "recurrence_type": "daily"})
    assert "actualizado" in result
    assert "todos los días" in result

    history = list_reminders.invoke({})
    assert "todos los días" in history
    assert "lunes" not in history


def test_update_reminder_daily_to_weekly_without_weekdays_is_rejected():
    from tools.reminder_tools import create_reminder, list_reminders, update_reminder

    create_reminder.invoke(
        {"message": "Tomar creatina", "time": "09:00", "recurrence_type": "daily"}
    )
    reminder_id = _extract_reminder_id(list_reminders.invoke({}))

    result = update_reminder.invoke({"reminder_id": reminder_id, "recurrence_type": "weekly"})
    assert "No se pudo actualizar" in result
    assert "weekdays" in result

    # No debe haber modificado nada: sigue siendo diario.
    history = list_reminders.invoke({})
    assert "todos los días" in history


def test_update_reminder_daily_with_explicit_weekdays_is_rejected():
    from tools.reminder_tools import create_reminder, list_reminders, update_reminder

    create_reminder.invoke(
        {
            "message": "Ir al gimnasio",
            "time": "18:00",
            "recurrence_type": "weekly",
            "weekdays": [0, 2, 4],
        }
    )
    reminder_id = _extract_reminder_id(list_reminders.invoke({}))

    result = update_reminder.invoke(
        {"reminder_id": reminder_id, "recurrence_type": "daily", "weekdays": [1, 3]}
    )
    assert "No se pudo actualizar" in result
    assert "weekdays" in result

    # No debe haber modificado nada: sigue siendo semanal con sus dias originales.
    history = list_reminders.invoke({})
    assert "lunes, miércoles, viernes" in history


def test_update_reminder_weekdays_only_replaces_and_sorts():
    from tools.reminder_tools import create_reminder, list_reminders, update_reminder

    create_reminder.invoke(
        {
            "message": "Ir al gimnasio",
            "time": "18:00",
            "recurrence_type": "weekly",
            "weekdays": [0, 2, 4],
        }
    )
    reminder_id = _extract_reminder_id(list_reminders.invoke({}))

    update_reminder.invoke({"reminder_id": reminder_id, "weekdays": [6, 1]})

    history = list_reminders.invoke({})
    assert "martes, domingo" in history


def test_update_reminder_nonexistent_id_does_not_modify_data():
    from tools.reminder_tools import list_reminders, update_reminder

    result = update_reminder.invoke({"reminder_id": 999999, "message": "No existe"})
    assert "No se pudo actualizar" in result
    assert "999999" in result
    assert "No hay recordatorios" in list_reminders.invoke({})


def test_update_reminder_invalid_time_does_not_modify_data():
    from tools.reminder_tools import create_reminder, list_reminders, update_reminder

    create_reminder.invoke(
        {"message": "Tomar creatina", "time": "09:00", "recurrence_type": "daily"}
    )
    reminder_id = _extract_reminder_id(list_reminders.invoke({}))

    result = update_reminder.invoke({"reminder_id": reminder_id, "time": "99:99"})
    assert "No se pudo actualizar" in result

    history = list_reminders.invoke({})
    assert "09:00" in history


def test_update_reminder_can_deactivate_and_reactivate():
    from tools.reminder_tools import create_reminder, list_reminders, update_reminder

    create_reminder.invoke(
        {"message": "Tomar creatina", "time": "09:00", "recurrence_type": "daily"}
    )
    reminder_id = _extract_reminder_id(list_reminders.invoke({}))

    update_reminder.invoke({"reminder_id": reminder_id, "is_active": False})
    assert "No hay recordatorios" in list_reminders.invoke({})

    update_reminder.invoke({"reminder_id": reminder_id, "is_active": True})
    assert "Tomar creatina" in list_reminders.invoke({})


# --- delete_reminder --------------------------------------------------------


def test_delete_reminder_removes_it():
    from tools.reminder_tools import create_reminder, delete_reminder, list_reminders

    create_reminder.invoke(
        {"message": "Tomar creatina", "time": "09:00", "recurrence_type": "daily"}
    )
    reminder_id = _extract_reminder_id(list_reminders.invoke({}))

    result = delete_reminder.invoke({"reminder_id": reminder_id})
    assert "eliminado" in result
    assert str(reminder_id) in result
    assert "No hay recordatorios" in list_reminders.invoke({})


def test_delete_reminder_nonexistent_id_does_not_modify_data():
    from tools.reminder_tools import create_reminder, delete_reminder, list_reminders

    create_reminder.invoke(
        {"message": "Tomar creatina", "time": "09:00", "recurrence_type": "daily"}
    )

    result = delete_reminder.invoke({"reminder_id": 999999})
    assert "No se pudo eliminar" in result
    assert "999999" in result
    assert "Tomar creatina" in list_reminders.invoke({})


def test_delete_reminder_does_not_affect_other_reminders():
    from tools.reminder_tools import create_reminder, delete_reminder, list_reminders

    create_reminder.invoke(
        {"message": "Tomar creatina", "time": "09:00", "recurrence_type": "daily"}
    )
    to_delete_id = _extract_reminder_id(list_reminders.invoke({}))
    create_reminder.invoke(
        {"message": "Ir al gimnasio", "time": "18:00", "recurrence_type": "daily"}
    )

    delete_reminder.invoke({"reminder_id": to_delete_id})

    history = list_reminders.invoke({})
    assert "Tomar creatina" not in history
    assert "Ir al gimnasio" in history


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
