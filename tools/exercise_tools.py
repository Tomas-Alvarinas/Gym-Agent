"""Tools para registrar, consultar, actualizar y eliminar sesiones de
ejercicio, serie por serie.

Regla de negocio (deliberadamente en código, no en el prompt): exercise y
al menos una serie son obligatorios. Por serie, reps y weight_kg son
ambos opcionales (un registro parcial sigue siendo válido: "hice 3
series pero no recuerdo peso ni reps"). Cada uno puede marcarse como
estimado, pero solo si tiene un valor: no se puede marcar como estimado
un dato desconocido (null). La date es opcional: si no se indica, el
sistema asigna el día actual; si se indica, debe venir en formato
YYYY-MM-DD estricto (se valida y se rechaza cualquier otro formato,
aunque sea un ISO 8601 válido en otra variante, como fechas de semana
o formato sin guiones). update_exercise_session y delete_exercise_session
reutilizan estas mismas validaciones (_validate_iso_date, _validate_sets)
en vez de duplicarlas.

session_id es un identificador interno (expuesto por get_exercise_history
para que el LLM lo use al llamar a update/delete); el usuario nunca
debería necesitar conocerlo ni escribirlo.

Nota: el código valida consistencia estructural (si está marcado como
estimado, tiene que tener valor), pero no puede verificar que una
estimación realmente provino del usuario y no fue inventada por el
agente -- eso depende de cómo el LLM decide llamar a esta tool, que es
una decisión de prompt engineering, no de esta capa. Tampoco implementa
confirmación antes de eliminar: eso también queda para el prompt.
"""
import re
from datetime import date as date_cls

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from data.exercise_logs import (
    delete_session_record,
    fetch_exercise_history,
    fetch_session_by_id,
    insert_exercise_log,
    update_session_record,
)

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ExerciseSet(BaseModel):
    weight_kg: float | None = Field(
        default=None, description="Peso usado en esta serie, si se conoce"
    )
    weight_is_estimated: bool = Field(
        default=False,
        description="True si weight_kg es un valor estimado por el usuario, no exacto",
    )
    reps: int | None = Field(
        default=None, description="Repeticiones realizadas en esta serie, si se conocen"
    )
    reps_is_estimated: bool = Field(
        default=False,
        description="True si reps es un valor estimado por el usuario, no exacto",
    )


def _format_weight(weight_kg: float | None, is_estimated: bool) -> str:
    if weight_kg is None:
        return "peso desconocido"
    prefix = "~" if is_estimated else ""
    return f"{prefix}{weight_kg} kg"


def _format_reps(reps: int | None, is_estimated: bool) -> str:
    if reps is None:
        return "reps desconocidas"
    prefix = "~" if is_estimated else ""
    return f"{prefix}{reps} reps"


def _format_set(s: dict) -> str:
    weight_part = _format_weight(s["weight_kg"], s["weight_is_estimated"])
    reps_part = _format_reps(s["reps"], s["reps_is_estimated"])
    return f"{weight_part}, {reps_part}"


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


def _validate_sets(sets: list[ExerciseSet]) -> str | None:
    """Devuelve un mensaje de error si alguna serie es inválida, o None si
    todas son válidas. Misma regla para log_exercise y update_exercise_session.
    """
    for i, s in enumerate(sets, start=1):
        if s.reps is not None and s.reps <= 0:
            return f"la serie {i} tiene 'reps' inválido (debe ser mayor a 0)."
        if s.reps is None and s.reps_is_estimated:
            return f"la serie {i} marca 'reps' como estimado pero no tiene valor."
        if s.weight_kg is not None and s.weight_kg < 0:
            return f"la serie {i} tiene 'weight_kg' inválido (no puede ser negativo)."
        if s.weight_kg is None and s.weight_is_estimated:
            return f"la serie {i} marca 'weight_kg' como estimado pero no tiene valor."
    return None


def _sets_to_data(sets: list[ExerciseSet]) -> list[dict]:
    return [
        {
            "reps": s.reps,
            "reps_is_estimated": s.reps_is_estimated,
            "weight_kg": s.weight_kg,
            "weight_is_estimated": s.weight_is_estimated,
        }
        for s in sets
    ]


@tool
def log_exercise(exercise: str, sets: list[ExerciseSet], date: str | None = None) -> str:
    """Registra un ejercicio realizado, con el detalle de cada serie individual.

    Cada elemento de 'sets' representa una serie. reps y weight_kg son
    ambos opcionales -- un registro parcial (ej. series sin recordar
    peso ni repeticiones) sigue siendo válido. weight_is_estimated /
    reps_is_estimated marcan si ese valor es una estimación en vez de un
    dato exacto; no pueden ser True si el valor correspondiente es
    desconocido. La cantidad de series es la cantidad de elementos de
    'sets'. 'date' es opcional en formato YYYY-MM-DD; si no se indica,
    se usa el día actual.
    """
    if not exercise or not exercise.strip():
        return "No se pudo registrar: falta el nombre del ejercicio."
    if not sets:
        return "No se pudo registrar: se necesita al menos una serie en 'sets'."

    if date is None:
        resolved_date = date_cls.today().isoformat()
    else:
        resolved_date = _validate_iso_date(date)
        if resolved_date is None:
            return f"No se pudo registrar: 'date' inválida ('{date}'). Debe tener formato YYYY-MM-DD."

    set_error = _validate_sets(sets)
    if set_error:
        return f"No se pudo registrar: {set_error}"

    exercise = exercise.strip()
    sets_data = _sets_to_data(sets)
    insert_exercise_log(exercise, sets_data, resolved_date)

    lines = [f"Registrado: {exercise} ({resolved_date})"]
    for s in sets_data:
        lines.append(f"- {_format_set(s)}")
    return "\n".join(lines)


@tool
def get_exercise_history(exercise: str) -> str:
    """Devuelve el historial de sesiones previas de un ejercicio específico, con el detalle de cada serie (incluyendo si un valor es exacto, estimado o desconocido), de la más reciente a la más antigua.

    Cada sesión incluye su session_id interno. Ese id es solo para uso de
    las tools (update_exercise_session / delete_exercise_session), nunca
    algo que el usuario deba conocer o escribir.
    """
    if not exercise or not exercise.strip():
        return "No se pudo consultar: falta el nombre del ejercicio."

    exercise = exercise.strip()
    sessions = fetch_exercise_history(exercise)
    if not sessions:
        return f"No hay registros de '{exercise}'."

    lines = [f"Historial de {exercise}:"]
    for session in sessions:
        sets_text = "; ".join(_format_set(s) for s in session["sets"])
        lines.append(
            f"- [session_id={session['session_id']}] {session['date']}: {sets_text}"
        )
    return "\n".join(lines)


@tool
def update_exercise_session(
    session_id: int,
    exercise: str | None = None,
    date: str | None = None,
    sets: list[ExerciseSet] | None = None,
) -> str:
    """Actualiza una sesión de entrenamiento existente, identificada por su session_id interno (obtenido de get_exercise_history).

    Solo se modifican los campos provistos explícitamente; los que se
    omiten (None) permanecen sin cambios. Si se provee 'sets', reemplaza
    por completo las series de esa sesión (misma validación que
    log_exercise: reps/weight_kg opcionales, is_estimated solo permitido
    junto con un valor). Si se provee 'date', debe tener formato
    YYYY-MM-DD estricto. Una entrada inválida no modifica nada.
    """
    session = fetch_session_by_id(session_id)
    if session is None:
        return f"No se pudo actualizar: no existe una sesión con session_id={session_id}."

    if exercise is not None and not exercise.strip():
        return "No se pudo actualizar: 'exercise' no puede ser vacío."

    resolved_date = session["date"]
    if date is not None:
        validated = _validate_iso_date(date)
        if validated is None:
            return f"No se pudo actualizar: 'date' inválida ('{date}'). Debe tener formato YYYY-MM-DD."
        resolved_date = validated

    sets_data = None
    if sets is not None:
        if not sets:
            return "No se pudo actualizar: 'sets' no puede ser una lista vacía."
        set_error = _validate_sets(sets)
        if set_error:
            return f"No se pudo actualizar: {set_error}"
        sets_data = _sets_to_data(sets)

    resolved_exercise = exercise.strip() if exercise is not None else session["exercise"]

    update_session_record(session_id, resolved_exercise, resolved_date, sets_data)

    return f"Sesión {session_id} actualizada: {resolved_exercise} ({resolved_date})."


@tool
def delete_exercise_session(session_id: int) -> str:
    """Elimina una sesión de entrenamiento existente (y todas sus series), identificada por su session_id interno (obtenido de get_exercise_history).

    No pide confirmación: elimina directamente si el session_id existe.
    """
    deleted = delete_session_record(session_id)
    if not deleted:
        return f"No se pudo eliminar: no existe una sesión con session_id={session_id}."
    return f"Sesión {session_id} eliminada."


TOOLS = [log_exercise, get_exercise_history, update_exercise_session, delete_exercise_session]
