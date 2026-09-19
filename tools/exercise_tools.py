"""Tools para registrar y consultar ejercicios realizados, serie por serie.

Regla de negocio (deliberadamente en código, no en el prompt): exercise y
al menos una serie son obligatorios. Por serie, reps y weight_kg son
ambos opcionales (un registro parcial sigue siendo válido: "hice 3
series pero no recuerdo peso ni reps"). Cada uno puede marcarse como
estimado, pero solo si tiene un valor: no se puede marcar como estimado
un dato desconocido (null). La date la asigna el sistema (hoy), nunca la
recibe como parámetro ni la decide el LLM.

Nota: el código valida consistencia estructural (si está marcado como
estimado, tiene que tener valor), pero no puede verificar que una
estimación realmente provino del usuario y no fue inventada por el
agente -- eso depende de cómo el LLM decide llamar a esta tool, que es
una decisión de prompt engineering, no de esta capa.
"""
from datetime import date as date_cls

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from data.exercise_logs import fetch_exercise_history, insert_exercise_log


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


@tool
def log_exercise(exercise: str, sets: list[ExerciseSet]) -> str:
    """Registra un ejercicio realizado hoy, con el detalle de cada serie individual.

    Cada elemento de 'sets' representa una serie. reps y weight_kg son
    ambos opcionales -- un registro parcial (ej. series sin recordar
    peso ni repeticiones) sigue siendo válido. weight_is_estimated /
    reps_is_estimated marcan si ese valor es una estimación en vez de un
    dato exacto; no pueden ser True si el valor correspondiente es
    desconocido. La cantidad de series es la cantidad de elementos de
    'sets'. La fecha se asigna automáticamente al día actual.
    """
    if not exercise or not exercise.strip():
        return "No se pudo registrar: falta el nombre del ejercicio."
    if not sets:
        return "No se pudo registrar: se necesita al menos una serie en 'sets'."

    for i, s in enumerate(sets, start=1):
        if s.reps is not None and s.reps <= 0:
            return f"No se pudo registrar: la serie {i} tiene 'reps' inválido (debe ser mayor a 0)."
        if s.reps is None and s.reps_is_estimated:
            return f"No se pudo registrar: la serie {i} marca 'reps' como estimado pero no tiene valor."
        if s.weight_kg is not None and s.weight_kg < 0:
            return f"No se pudo registrar: la serie {i} tiene 'weight_kg' inválido (no puede ser negativo)."
        if s.weight_kg is None and s.weight_is_estimated:
            return f"No se pudo registrar: la serie {i} marca 'weight_kg' como estimado pero no tiene valor."

    exercise = exercise.strip()
    today = date_cls.today().isoformat()
    sets_data = [
        {
            "reps": s.reps,
            "reps_is_estimated": s.reps_is_estimated,
            "weight_kg": s.weight_kg,
            "weight_is_estimated": s.weight_is_estimated,
        }
        for s in sets
    ]
    insert_exercise_log(exercise, sets_data, today)

    lines = [f"Registrado: {exercise} ({today})"]
    for s in sets_data:
        lines.append(f"- {_format_set(s)}")
    return "\n".join(lines)


@tool
def get_exercise_history(exercise: str) -> str:
    """Devuelve el historial de sesiones previas de un ejercicio específico, con el detalle de cada serie (incluyendo si un valor es exacto, estimado o desconocido), de la más reciente a la más antigua."""
    if not exercise or not exercise.strip():
        return "No se pudo consultar: falta el nombre del ejercicio."

    exercise = exercise.strip()
    sessions = fetch_exercise_history(exercise)
    if not sessions:
        return f"No hay registros de '{exercise}'."

    lines = [f"Historial de {exercise}:"]
    for session in sessions:
        sets_text = "; ".join(_format_set(s) for s in session["sets"])
        lines.append(f"- {session['date']}: {sets_text}")
    return "\n".join(lines)


TOOLS = [log_exercise, get_exercise_history]
