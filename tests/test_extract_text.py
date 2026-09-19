"""Prueba local de cli.extract_text(), sin dependencias externas (asserts planos).

Ejecutar con: python tests/test_extract_text.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage

from cli import extract_text


def test_extract_text_from_string_content():
    message = AIMessage(content="Hoy te toca: Pecho y triceps")
    assert extract_text(message) == "Hoy te toca: Pecho y triceps"


def test_extract_text_from_gemini_content_blocks():
    # Estructura exacta reportada como bug: lista de content blocks con
    # extras/signature que no deben aparecer en la salida.
    message = AIMessage(content=[
        {
            "type": "text",
            "text": "No puedo inventar entrenamientos.",
            "extras": {"signature": "abc123signature"},
        }
    ])
    assert extract_text(message) == "No puedo inventar entrenamientos."


def test_extract_text_ignores_non_text_blocks():
    message = AIMessage(content=[
        {"type": "text", "text": "Parte visible."},
        {"type": "thinking", "thinking": "razonamiento interno, no debe mostrarse"},
    ])
    assert extract_text(message) == "Parte visible."


def test_extract_text_concatenates_multiple_text_blocks():
    message = AIMessage(content=[
        {"type": "text", "text": "Primera parte. "},
        {"type": "text", "text": "Segunda parte."},
    ])
    assert extract_text(message) == "Primera parte. Segunda parte."


if __name__ == "__main__":
    test_extract_text_from_string_content()
    test_extract_text_from_gemini_content_blocks()
    test_extract_text_ignores_non_text_blocks()
    test_extract_text_concatenates_multiple_text_blocks()
    print("OK: las 4 pruebas de extract_text() pasaron correctamente.")
