"""Configuración del proyecto: carga de variables de entorno y selección del LLM.

Mantener esto separado del agente permite cambiar de proveedor/modelo
sin tocar la lógica de prompts, tools o grafo.
"""
import os

from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-5")


def get_llm():
    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=LLM_MODEL, temperature=0)

    raise ValueError(f"Proveedor de LLM no soportado: {LLM_PROVIDER}")
