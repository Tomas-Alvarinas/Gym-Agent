"""Configuración del proyecto: carga de variables de entorno y selección del LLM.

Mantener esto separado del agente permite cambiar de proveedor/modelo
sin tocar la lógica de prompts, tools o grafo.
"""
import os

from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

# Usadas por telegram_notifier.py / scheduler.py (V3.2). Nunca hardcodear
# el valor real acá: siempre vienen de .env (gitignored).
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def get_llm():
    if LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=0)

    raise ValueError(f"Proveedor de LLM no soportado: {LLM_PROVIDER}")
