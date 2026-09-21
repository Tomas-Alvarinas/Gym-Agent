"""Scheduler de recordatorios: proceso independiente que convierte los
reminders guardados en SQLite en notificaciones reales por Telegram.

No se importa desde agent/graph.py, tools/ ni cli.py -- es un programa
aparte que se corre con `python scheduler.py`. El agente conversacional
decide QUÉ recordatorios existen; este proceso solo lee esa tabla
periódicamente y actúa.

Diseño de la decisión "¿corresponde disparar esto ahora?" (should_trigger):
determinística, sin I/O, sin LLM -- recibe un dict de reminder y un
datetime 'now' y devuelve un bool. Eso es lo que la hace testeable de
forma aislada, sin DB ni red.

Ventana de tolerancia: 5 minutos hacia adelante desde la hora programada
de hoy (scheduled_occurrence). Cubre pausas breves del proceso (el tick
duerme hasta el próximo minuto exacto, pero un hiccup del sistema puede
atrasarlo unos segundos o minutos); no es una recuperación de
recordatorios perdidos por horas -- eso queda fuera de alcance.

Deduplicación: last_triggered_at guarda el instante ISO timezone-aware
del último envío EXITOSO. Un reminder se considera ya cubierto para la
ocurrencia de hoy si last_triggered_at >= scheduled_occurrence (no
igualdad estricta: el envío real puede caer unos segundos/minutos
después del horario exacto, dentro de la ventana). Como occurrence se
recalcula desde el 'time' actual del reminder en cada tick, cambiar la
hora de un reminder a mitad del día ya enviado hace que la comparación
se resuelva sola: adelantarla habilita un nuevo envío hoy, atrasarla no
lo hace.
"""
import time
from datetime import datetime, timedelta

from data.reminders import fetch_reminders, mark_reminder_triggered
from date_utils import now_in_argentina
from telegram_notifier import send_telegram_message

TOLERANCE = timedelta(minutes=5)


def scheduled_occurrence_for_today(reminder: dict, now: datetime) -> datetime | None:
    """Devuelve el datetime (aware, misma tz que 'now') de la ocurrencia
    de HOY para este reminder, o None si hoy no le corresponde (weekly
    en un día no incluido en weekdays).
    """
    if reminder["recurrence_type"] == "weekly":
        weekdays = reminder["weekdays"] or []
        if now.weekday() not in weekdays:
            return None

    hour, minute = (int(part) for part in reminder["time"].split(":"))
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)


def should_trigger(reminder: dict, now: datetime, tolerance: timedelta = TOLERANCE) -> bool:
    """Decide si HOY, en el instante 'now', corresponde disparar este
    reminder. Pura y determinística: nada de I/O, nada de LLM.
    """
    if not reminder["is_active"]:
        return False

    occurrence = scheduled_occurrence_for_today(reminder, now)
    if occurrence is None:
        return False

    if not (occurrence <= now <= occurrence + tolerance):
        return False

    last_triggered_at = reminder.get("last_triggered_at")
    if last_triggered_at:
        last = datetime.fromisoformat(last_triggered_at)
        if last >= occurrence:
            return False

    return True


def run_tick(now: datetime | None = None, db_path=None) -> list[int]:
    """Ejecuta un tick: revisa todos los reminders activos, envía los que
    correspondan y marca last_triggered_at solo en los envíos exitosos.

    Devuelve la lista de reminder_id efectivamente enviados en este tick.
    """
    if now is None:
        now = now_in_argentina()

    triggered_ids = []
    for reminder in fetch_reminders(active_only=True, db_path=db_path):
        try:
            if not should_trigger(reminder, now):
                continue
        except (ValueError, KeyError):
            # Un reminder con datos mal formados no debe tirar abajo el
            # tick completo -- se lo salta y se sigue con el resto.
            continue

        sent = send_telegram_message(f"Recordatorio: {reminder['message']}")
        if sent:
            mark_reminder_triggered(reminder["id"], now.isoformat(), db_path=db_path)
            triggered_ids.append(reminder["id"])

    return triggered_ids


def _seconds_until_next_minute(now: datetime) -> float:
    next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    return (next_minute - now).total_seconds()


def main():
    print("Gym Agent scheduler iniciado (Argentina). Ctrl+C para detener.")
    while True:
        run_tick()
        time.sleep(_seconds_until_next_minute(now_in_argentina()))


if __name__ == "__main__":
    main()
