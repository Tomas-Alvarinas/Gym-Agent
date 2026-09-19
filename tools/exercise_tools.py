"""Tools para registrar y consultar ejercicios realizados, serie por serie.

Regla de negocio (deliberadamente en código, no en el prompt): exercise y
al menos una serie son obligatorios; cada serie requiere reps > 0 y
weight_kg opcional pero no negativo si se da. La date la asigna el
sistema (hoy), nunca la recibe como parámetro ni la decide el LLM. Si
algo obligatorio falta o es inválido, la tool devuelve un error explícito
en vez de guardar o inventar el dato.
"""
from datetime import date as date_cls

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from data.exercise_logs import fetch_exercise_history, insert_exercise_log


class ExerciseSet(BaseModel):
    reps: int = Field(description="Repeticiones realizadas en esta serie")
    weight_kg: float | None = Field(
        default=None, description="Peso usado en esta serie, si aplica"
    )


def _format_set(reps: int, weight_kg: float | None) -> str:
    if weight_kg is not None:
        return f"{weight_kg} kg x {reps}"
    return f"{reps} reps"


@tool
def log_exercise(exercise: str, sets: list[ExerciseSet]) -> str:
    """Registra un ejercicio realizado hoy, con el detalle de cada serie individual.

    Cada elemento de 'sets' representa una serie: reps es obligatorio,
    weight_kg es opcional (ejercicios sin peso externo, como flexiones,
    no lo necesitan). La cantidad de series es la cantidad de elementos
    de 'sets'. La fecha se asigna automáticamente al día actual.
    """
    if not exercise or not exercise.strip():
        return "No se pudo registrar: falta el nombre del ejercicio."
    if not sets:
        return "No se pudo registrar: se necesita al menos una serie en 'sets'."

    for i, s in enumerate(sets, start=1):
        if s.reps <= 0:
            return f"No se pudo registrar: la serie {i} tiene 'reps' inválido (debe ser mayor a 0)."
        if s.weight_kg is not None and s.weight_kg < 0:
            return f"No se pudo registrar: la serie {i} tiene 'weight_kg' inválido (no puede ser negativo)."

    exercise = exercise.strip()
    today = date_cls.today().isoformat()
    sets_data = [{"reps": s.reps, "weight_kg": s.weight_kg} for s in sets]
    insert_exercise_log(exercise, sets_data, today)

    lines = [f"Registrado: {exercise} ({today})"]
    for s in sets_data:
        lines.append(f"- {_format_set(s['reps'], s['weight_kg'])}")
    return "\n".join(lines)


@tool
def get_exercise_history(exercise: str) -> str:
    """Devuelve el historial de sesiones previas de un ejercicio específico, con el detalle de cada serie, de la más reciente a la más antigua."""
    if not exercise or not exercise.strip():
        return "No se pudo consultar: falta el nombre del ejercicio."

    exercise = exercise.strip()
    sessions = fetch_exercise_history(exercise)
    if not sessions:
        return f"No hay registros de '{exercise}'."

    lines = [f"Historial de {exercise}:"]
    for session in sessions:
        sets_text = ", ".join(
            _format_set(s["reps"], s["weight_kg"]) for s in session["sets"]
        )
        lines.append(f"- {session['date']}: {sets_text}")
    return "\n".join(lines)


TOOLS = [log_exercise, get_exercise_history]
