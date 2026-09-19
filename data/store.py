"""Capa de acceso a datos.

V1: lee la rutina desde un JSON fijo. Esto es intencionalmente el único
punto del código que sabe de dónde vienen los datos, para poder
reemplazarlo por SQLite más adelante sin tocar tools ni el agente.
"""
import json
from pathlib import Path

ROUTINE_PATH = Path(__file__).parent / "fixtures" / "routine.json"


def get_routine_for_day(day_name: str) -> dict | None:
    """day_name en minúsculas en inglés: 'monday', 'tuesday', etc."""
    with open(ROUTINE_PATH, encoding="utf-8") as f:
        routine = json.load(f)
    return routine.get(day_name)
