"""Tools relacionadas con el entrenamiento del día.

Regla de negocio importante (deliberadamente en código, no en el prompt):
qué se considera "hoy" y qué se devuelve si es día de descanso o si no
hay rutina cargada, NO lo decide el LLM. La tool siempre devuelve datos
reales o un mensaje explícito de "no hay información" — nunca inventa.
"""
from langchain_core.tools import tool

from data.store import get_routine_for_day
from date_utils import today_in_argentina

_WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


@tool
def get_today_workout() -> str:
    """Devuelve el entrenamiento correspondiente al día actual.

    Usar esta tool cuando el usuario pregunte qué le toca entrenar hoy.
    """
    day_name = _WEEKDAYS[today_in_argentina().weekday()]
    routine = get_routine_for_day(day_name)

    if routine is None:
        return f"No hay rutina cargada para el día '{day_name}'."

    if not routine["exercises"]:
        return f"Hoy ({day_name}) es día de descanso según tu rutina."

    lines = [f"Hoy ({day_name}) te toca: {routine['focus']}"]
    for ex in routine["exercises"]:
        lines.append(f"- {ex['name']}: {ex['sets']} series x {ex['reps']}")
    return "\n".join(lines)


TOOLS = [get_today_workout]
