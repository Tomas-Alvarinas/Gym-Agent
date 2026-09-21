"""Tools para crear, consultar, actualizar y eliminar objetivos de
rendimiento por ejercicio.

exercise_goals es independiente de exercise_sessions/exercise_sets: el
objetivo (lo que quiero alcanzar) y el historial (lo que realmente hice)
son conceptos distintos, sin relación estructural entre ambos. Para
analizar progreso ("¿cómo vengo con mi objetivo de X?") no hay una tool
de análisis dedicada -- el LLM combina list_exercise_goals con
get_exercise_history (tools/exercise_tools.py) y razona sobre ambas.

Regla de negocio (en código, no en el prompt): exercise, target_weight_kg
y target_reps son obligatorios; target_weight_kg y target_reps deben
ser estrictamente mayores a 0 (objetivos de repeticiones sin peso, como
dominadas sin lastre, no están soportados en V4.1). target_date es
opcional, YYYY-MM-DD estricto. Solo puede haber un objetivo ACTIVO por
ejercicio (case-insensitive) -- garantizado en código (chequeo previo a
create/update) y también por un índice único parcial en data/db.py
como respaldo a nivel de base de datos.

goal_id es un identificador interno (expuesto por list_exercise_goals
para que el LLM lo use en update/delete); el usuario nunca debería
necesitar conocerlo ni escribirlo.

Nota: delete_exercise_goal no implementa confirmación -- elimina
directo si el goal_id existe. La confirmación conversacional antes de
eliminar es una decisión de prompt engineering, no de esta capa.
"""
import re
from datetime import date as date_cls

from langchain_core.tools import tool

from data.exercise_goals import (
    delete_exercise_goal_record,
    fetch_active_goal_by_exercise,
    fetch_exercise_goal_by_id,
    fetch_exercise_goals,
    insert_exercise_goal,
    update_exercise_goal_record,
)
from date_utils import now_in_argentina

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_iso_date(date: str) -> str | None:
    """Devuelve la fecha normalizada si 'date' es YYYY-MM-DD estricto y
    válida, o None si no lo es (formato incorrecto o fecha inexistente).
    """
    if not _ISO_DATE_RE.match(date):
        return None
    try:
        return date_cls.fromisoformat(date).isoformat()
    except ValueError:
        return None


def _format_goal(
    exercise: str,
    target_weight_kg: float,
    target_reps: int,
    target_date: str | None,
    is_active: bool = True,
) -> str:
    date_part = f" (fecha objetivo: {target_date})" if target_date else ""
    status_part = "" if is_active else " [inactivo]"
    return f"{exercise}: {target_weight_kg} kg x {target_reps} reps{date_part}{status_part}"


@tool
def create_exercise_goal(
    exercise: str,
    target_weight_kg: float,
    target_reps: int,
    target_date: str | None = None,
) -> str:
    """Crea un objetivo de rendimiento para un ejercicio.

    target_weight_kg y target_reps son obligatorios y deben ser
    estrictamente mayores a 0. target_date es opcional, en formato
    YYYY-MM-DD. Solo puede existir un objetivo activo por ejercicio: si
    ya existe uno, esta tool lo rechaza en vez de reemplazarlo -- para
    modificar un objetivo existente hay que usar update_exercise_goal.
    """
    if not exercise or not exercise.strip():
        return "No se pudo crear el objetivo: falta el nombre del ejercicio."

    if target_weight_kg <= 0:
        return "No se pudo crear el objetivo: 'target_weight_kg' debe ser mayor a 0."

    if target_reps <= 0:
        return "No se pudo crear el objetivo: 'target_reps' debe ser mayor a 0."

    resolved_target_date = None
    if target_date is not None:
        resolved_target_date = _validate_iso_date(target_date)
        if resolved_target_date is None:
            return f"No se pudo crear el objetivo: 'target_date' inválida ('{target_date}'). Debe tener formato YYYY-MM-DD."

    exercise = exercise.strip()

    existing = fetch_active_goal_by_exercise(exercise)
    if existing is not None:
        existing_text = _format_goal(
            existing["exercise"], existing["target_weight_kg"], existing["target_reps"], existing["target_date"]
        )
        return (
            f"No se pudo crear el objetivo: ya existe un objetivo activo para "
            f"'{exercise}' ({existing_text}). Usá update_exercise_goal para modificarlo."
        )

    created_at = now_in_argentina().isoformat()
    goal_id = insert_exercise_goal(
        exercise, target_weight_kg, target_reps, resolved_target_date, created_at
    )

    formatted = _format_goal(exercise, target_weight_kg, target_reps, resolved_target_date)
    return f"Objetivo creado: [goal_id={goal_id}] {formatted}"


@tool
def list_exercise_goals(include_inactive: bool = False) -> str:
    """Devuelve los objetivos de rendimiento existentes (solo activos por defecto; todos si include_inactive=True).

    Cada objetivo incluye su goal_id interno, solo para uso de las
    tools (update_exercise_goal / delete_exercise_goal) -- nunca algo
    que el usuario deba conocer o escribir. Para analizar el progreso
    hacia un objetivo, combinar el resultado de esta tool con
    get_exercise_history del mismo ejercicio.
    """
    goals = fetch_exercise_goals(active_only=not include_inactive)
    if not goals:
        return "No hay objetivos."

    lines = ["Objetivos:"]
    for g in goals:
        formatted = _format_goal(
            g["exercise"], g["target_weight_kg"], g["target_reps"], g["target_date"], g["is_active"]
        )
        lines.append(f"- [goal_id={g['id']}] {formatted}")
    return "\n".join(lines)


@tool
def update_exercise_goal(
    goal_id: int,
    exercise: str | None = None,
    target_weight_kg: float | None = None,
    target_reps: int | None = None,
    target_date: str | None = None,
    clear_target_date: bool = False,
    is_active: bool | None = None,
) -> str:
    """Actualiza un objetivo existente, identificado por su goal_id interno (obtenido de list_exercise_goals).

    Solo se modifican los campos provistos explícitamente; los que se
    omiten (None) permanecen sin cambios. Para 'target_date': omitirlo
    preserva el valor actual; darle un valor YYYY-MM-DD lo establece o
    cambia; para BORRAR una fecha ya puesta, usar clear_target_date=True
    sin proveer target_date en la misma llamada (proveer ambos a la vez
    se rechaza). Si el cambio resultante (ej. renombrar 'exercise' o
    reactivar con is_active=True) chocaría con otro objetivo activo
    existente para el mismo ejercicio, se rechaza sin modificar nada.
    """
    goal = fetch_exercise_goal_by_id(goal_id)
    if goal is None:
        return f"No se pudo actualizar: no existe un objetivo con goal_id={goal_id}."

    if exercise is not None and not exercise.strip():
        return "No se pudo actualizar: 'exercise' no puede ser vacío."

    if target_weight_kg is not None and target_weight_kg <= 0:
        return "No se pudo actualizar: 'target_weight_kg' debe ser mayor a 0."

    if target_reps is not None and target_reps <= 0:
        return "No se pudo actualizar: 'target_reps' debe ser mayor a 0."

    if target_date is not None and clear_target_date:
        return "No se pudo actualizar: no se puede indicar 'target_date' y 'clear_target_date' al mismo tiempo."

    if clear_target_date:
        resolved_target_date = None
    elif target_date is not None:
        resolved_target_date = _validate_iso_date(target_date)
        if resolved_target_date is None:
            return f"No se pudo actualizar: 'target_date' inválida ('{target_date}'). Debe tener formato YYYY-MM-DD."
    else:
        resolved_target_date = goal["target_date"]

    resolved_exercise = exercise.strip() if exercise is not None else goal["exercise"]
    resolved_target_weight_kg = (
        target_weight_kg if target_weight_kg is not None else goal["target_weight_kg"]
    )
    resolved_target_reps = target_reps if target_reps is not None else goal["target_reps"]
    resolved_is_active = is_active if is_active is not None else goal["is_active"]

    if resolved_is_active:
        conflicting = fetch_active_goal_by_exercise(resolved_exercise)
        if conflicting is not None and conflicting["id"] != goal_id:
            conflicting_text = _format_goal(
                conflicting["exercise"],
                conflicting["target_weight_kg"],
                conflicting["target_reps"],
                conflicting["target_date"],
            )
            return (
                f"No se pudo actualizar: ya existe otro objetivo activo para "
                f"'{resolved_exercise}' ({conflicting_text})."
            )

    update_exercise_goal_record(
        goal_id,
        resolved_exercise,
        resolved_target_weight_kg,
        resolved_target_reps,
        resolved_target_date,
        resolved_is_active,
    )

    formatted = _format_goal(
        resolved_exercise,
        resolved_target_weight_kg,
        resolved_target_reps,
        resolved_target_date,
        resolved_is_active,
    )
    return f"Objetivo {goal_id} actualizado: {formatted}"


@tool
def delete_exercise_goal(goal_id: int) -> str:
    """Elimina un objetivo existente, identificado por su goal_id interno (obtenido de list_exercise_goals).

    No pide confirmación: elimina directamente si el goal_id existe.
    """
    deleted = delete_exercise_goal_record(goal_id)
    if not deleted:
        return f"No se pudo eliminar: no existe un objetivo con goal_id={goal_id}."
    return f"Objetivo {goal_id} eliminado."


TOOLS = [create_exercise_goal, list_exercise_goals, update_exercise_goal, delete_exercise_goal]
