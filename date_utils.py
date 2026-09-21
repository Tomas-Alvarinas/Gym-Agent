"""Fuente de verdad determinística para "ahora"/"hoy" en Argentina.

Se usa en el contexto que agent/graph.py le manda al LLM en cada turno,
en los fallbacks de fecha de log_exercise y get_today_workout, y en
created_at de reminders -- todos evitando datetime.now()/date.today()
(hora LOCAL DEL PROCESO, no de Argentina). Eso importa porque el
proceso puede correr en un host en otro huso horario (ej. UTC, como
este mismo entorno de desarrollo) -- ahí el día calendario del
servidor se adelanta al de Argentina durante varias horas por día.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def now_in_argentina(now: datetime | None = None) -> datetime:
    """Instante actual, aware, en la zona horaria de Argentina (UTC-3,
    sin horario de verano desde 2009).

    now: instante aware opcional, para inyectar en tests. En producción
    siempre se omite y se usa el reloj real del sistema.
    """
    if now is None:
        now = datetime.now(ARGENTINA_TZ)
    return now.astimezone(ARGENTINA_TZ)


def today_in_argentina(now: datetime | None = None) -> date:
    """Fecha actual en Argentina. Ver now_in_argentina() para el parámetro 'now'."""
    return now_in_argentina(now).date()
