"""Configuración del proyecto: carga de variables de entorno y selección del LLM.

Mantener esto separado del agente permite cambiar de proveedor/modelo
sin tocar la lógica de prompts, tools o grafo.
"""
import os

from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")


def get_llm():
    if LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=0)

    raise ValueError(f"Proveedor de LLM no soportado: {LLM_PROVIDER}")
