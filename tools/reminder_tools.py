"""Tools para crear, consultar, actualizar y eliminar recordatorios.

Modelo de recurrencia (deliberadamente simple, dos columnas explícitas
en vez de una representación colapsada -- decisión de producto: la
representación persistida debe ser explícita y quedar preparada para
el scheduler de V3.2):

    recurrence_type == "daily"  -> weekdays debe ser None.
    recurrence_type == "weekly" -> weekdays debe tener 1 a 7 enteros
                                    únicos entre 0 (lunes) y 6 (domingo).

Regla de negocio (en código, no en el prompt): message y time son
obligatorios; time debe ser HH:MM estricto (24hs); la combinación
recurrence_type/weekdays se valida siempre sobre el ESTADO FINAL (tras
combinar lo provisto con lo existente en update_reminder), nunca sobre
los campos aislados. category es texto libre opcional. La hora y el
huso horario de creación (created_at, timezone) los asigna el sistema
via date_utils, nunca el LLM.

reminder_id es un identificador interno (expuesto por list_reminders
para que el LLM lo use en update/delete); el usuario nunca debería
necesitar conocerlo ni escribirlo.

Nota: delete_reminder no implementa confirmación -- elimina directo si
el reminder_id existe. La confirmación conversacional antes de borrar
es una decisión de prompt engineering, no de esta capa.
"""
import re

from langchain_core.tools import tool

from data.reminders import (
    delete_reminder_record,
    fetch_reminder_by_id,
    fetch_reminders,
    insert_reminder,
    update_reminder_record,
)
from date_utils import ARGENTINA_TZ, now_in_argentina

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

_WEEKDAY_NAMES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _validate_time(time: str) -> bool:
    return bool(_TIME_RE.match(time))


def _validate_recurrence(recurrence_type: str, weekdays: list[int] | None) -> str | None:
    """Devuelve un mensaje de error si la combinación recurrence_type/weekdays
    es inválida, o None si es válida.
    """
    if recurrence_type not in ("daily", "weekly"):
        return "'recurrence_type' debe ser 'daily' o 'weekly'."

    if recurrence_type == "daily":
        if weekdays:
            return (
                "'recurrence_type' es 'daily', pero se proveyeron 'weekdays'; "
                "un recordatorio diario no debe tener días específicos."
            )
        return None

    # weekly
    if not weekdays:
        return "'recurrence_type' es 'weekly', pero no se proveyó 'weekdays' (al menos un día)."
    if any(d < 0 or d > 6 for d in weekdays):
        return "'weekdays' debe contener valores entre 0 (lunes) y 6 (domingo)."
    if len(set(weekdays)) != len(weekdays):
        return "'weekdays' no puede tener días duplicados."
    return None


def _format_recurrence(recurrence_type: str, weekdays: list[int] | None) -> str:
    if recurrence_type == "daily":
        return "todos los días"
    return ", ".join(_WEEKDAY_NAMES[d] for d in weekdays)


def _format_reminder(
    message: str,
    category: str | None,
    time: str,
    recurrence_type: str,
    weekdays: list[int] | None,
    is_active: bool = True,
) -> str:
    category_part = f" ({category})" if category else ""
    status_part = "" if is_active else " [inactivo]"
    recurrence_text = _format_recurrence(recurrence_type, weekdays)
    return f"{message}{category_part} — {time}, {recurrence_text}{status_part}"


@tool
def create_reminder(
    message: str,
    time: str,
    recurrence_type: str,
    weekdays: list[int] | None = None,
    category: str | None = None,
) -> str:
    """Crea un recordatorio nuevo.

    time: hora en formato HH:MM (24hs). recurrence_type: "daily" o
    "weekly". weekdays: obligatorio si recurrence_type es "weekly"
    (lista de enteros 0=lunes..6=domingo, sin duplicados); debe
    omitirse si recurrence_type es "daily". category es un texto libre
    opcional (ej. "suplementos", "entrenamiento").
    """
    if not message or not message.strip():
        return "No se pudo crear el recordatorio: falta el mensaje."

    if not _validate_time(time):
        return f"No se pudo crear el recordatorio: 'time' inválido ('{time}'). Debe tener formato HH:MM (24hs)."

    recurrence_error = _validate_recurrence(recurrence_type, weekdays)
    if recurrence_error:
        return f"No se pudo crear el recordatorio: {recurrence_error}"

    resolved_weekdays = None if recurrence_type == "daily" else sorted(weekdays)
    resolved_category = category.strip() if category is not None and category.strip() else None
    resolved_message = message.strip()

    created_at = now_in_argentina().isoformat()
    reminder_id = insert_reminder(
        resolved_message,
        resolved_category,
        time,
        recurrence_type,
        resolved_weekdays,
        ARGENTINA_TZ.key,
        created_at,
    )

    formatted = _format_reminder(
        resolved_message, resolved_category, time, recurrence_type, resolved_weekdays
    )
    return f"Recordatorio creado: [reminder_id={reminder_id}] {formatted}"


@tool
def list_reminders(include_inactive: bool = False) -> str:
    """Devuelve los recordatorios existentes (solo activos por defecto; todos si include_inactive=True), con el detalle de cada uno.

    Cada recordatorio incluye su reminder_id interno. Ese id es solo
    para uso de las tools (update_reminder / delete_reminder), nunca
    algo que el usuario deba conocer o escribir.
    """
    reminders = fetch_reminders(active_only=not include_inactive)
    if not reminders:
        return "No hay recordatorios."

    lines = ["Recordatorios:"]
    for r in reminders:
        formatted = _format_reminder(
            r["message"], r["category"], r["time"], r["recurrence_type"], r["weekdays"], r["is_active"]
        )
        lines.append(f"- [reminder_id={r['id']}] {formatted}")
    return "\n".join(lines)


@tool
def update_reminder(
    reminder_id: int,
    message: str | None = None,
    time: str | None = None,
    recurrence_type: str | None = None,
    weekdays: list[int] | None = None,
    category: str | None = None,
    is_active: bool | None = None,
) -> str:
    """Actualiza un recordatorio existente, identificado por su reminder_id interno (obtenido de list_reminders).

    Solo se modifican los campos provistos explícitamente; los que se
    omiten (None) permanecen sin cambios. Si se cambia recurrence_type
    a "daily" sin proveer 'weekdays' en el mismo llamado, los días
    específicos anteriores se descartan automáticamente (un recordatorio
    diario no tiene días). Si se cambia a "weekly" sin proveer
    'weekdays', hace falta indicarlos explícitamente en ese mismo
    llamado. Cualquier combinación resultante inválida se rechaza sin
    modificar nada.
    """
    reminder = fetch_reminder_by_id(reminder_id)
    if reminder is None:
        return f"No se pudo actualizar: no existe un recordatorio con reminder_id={reminder_id}."

    if message is not None and not message.strip():
        return "No se pudo actualizar: 'message' no puede ser vacío."

    if time is not None and not _validate_time(time):
        return f"No se pudo actualizar: 'time' inválido ('{time}'). Debe tener formato HH:MM (24hs)."

    resolved_recurrence_type = (
        recurrence_type if recurrence_type is not None else reminder["recurrence_type"]
    )

    if weekdays is not None:
        resolved_weekdays = weekdays
    elif recurrence_type is not None and resolved_recurrence_type == "daily":
        # Cambia a diario en este llamado sin tocar 'weekdays': no se
        # arrastran días específicos de un estado semanal anterior.
        resolved_weekdays = None
    else:
        resolved_weekdays = reminder["weekdays"]

    recurrence_error = _validate_recurrence(resolved_recurrence_type, resolved_weekdays)
    if recurrence_error:
        return f"No se pudo actualizar: {recurrence_error}"

    resolved_weekdays = (
        None if resolved_recurrence_type == "daily" else sorted(resolved_weekdays)
    )
    resolved_message = message.strip() if message is not None else reminder["message"]
    resolved_time = time if time is not None else reminder["time"]
    resolved_category = (
        (category.strip() or None) if category is not None else reminder["category"]
    )
    resolved_is_active = is_active if is_active is not None else reminder["is_active"]

    update_reminder_record(
        reminder_id,
        resolved_message,
        resolved_category,
        resolved_time,
        resolved_recurrence_type,
        resolved_weekdays,
        reminder["timezone"],
        resolved_is_active,
    )

    formatted = _format_reminder(
        resolved_message,
        resolved_category,
        resolved_time,
        resolved_recurrence_type,
        resolved_weekdays,
        resolved_is_active,
    )
    return f"Recordatorio {reminder_id} actualizado: {formatted}"


@tool
def delete_reminder(reminder_id: int) -> str:
    """Elimina un recordatorio existente, identificado por su reminder_id interno (obtenido de list_reminders).

    No pide confirmación: elimina directamente si el reminder_id existe.
    """
    deleted = delete_reminder_record(reminder_id)
    if not deleted:
        return f"No se pudo eliminar: no existe un recordatorio con reminder_id={reminder_id}."
    return f"Recordatorio {reminder_id} eliminado."


TOOLS = [create_reminder, list_reminders, update_reminder, delete_reminder]
