"""Tools para registrar y consultar ejercicios realizados.

Regla de negocio (deliberadamente en código, no en el prompt): exercise,
sets y reps son obligatorios y deben tener un valor válido (> 0);
weight_kg es opcional pero si se da no puede ser negativo. La date la
asigna el sistema (hoy), nunca la recibe como parámetro ni la decide el
LLM. Si algo obligatorio falta o es inválido, la tool devuelve un error
explícito en vez de guardar o inventar el dato.
"""
from datetime import date as date_cls

from langchain_core.tools import tool

from data.exercise_logs import fetch_exercise_history, insert_exercise_log


@tool
def log_exercise(
    exercise: str, sets: int, reps: int, weight_kg: float | None = None
) -> str:
    """Registra un ejercicio realizado hoy, con series, repeticiones y opcionalmente el peso usado.

    La fecha se asigna automáticamente al día actual; no se recibe como parámetro.
    """
    if not exercise or not exercise.strip():
        return "No se pudo registrar: falta el nombre del ejercicio."
    if sets <= 0:
        return "No se pudo registrar: 'sets' debe ser mayor a 0."
    if reps <= 0:
        return "No se pudo registrar: 'reps' debe ser mayor a 0."
    if weight_kg is not None and weight_kg < 0:
        return "No se pudo registrar: 'weight_kg' no puede ser negativo."

    exercise = exercise.strip()
    today = date_cls.today().isoformat()
    insert_exercise_log(exercise, sets, reps, today, weight_kg)

    weight_part = f", {weight_kg} kg" if weight_kg is not None else ""
    return f"Registrado: {exercise} - {sets}x{reps}{weight_part} ({today})"


@tool
def get_exercise_history(exercise: str) -> str:
    """Devuelve el historial de registros previos de un ejercicio específico, del más reciente al más antiguo."""
    if not exercise or not exercise.strip():
        return "No se pudo consultar: falta el nombre del ejercicio."

    exercise = exercise.strip()
    records = fetch_exercise_history(exercise)
    if not records:
        return f"No hay registros de '{exercise}'."

    lines = [f"Historial de {exercise}:"]
    for r in records:
        weight_part = f", {r['weight_kg']} kg" if r["weight_kg"] is not None else ""
        lines.append(f"- {r['date']}: {r['sets']}x{r['reps']}{weight_part}")
    return "\n".join(lines)


TOOLS = [log_exercise, get_exercise_history]
