"""Prueba de agent_node: el contexto de fecha actual (Argentina) debe
llegar como mensaje al LLM en cada invocación del grafo, calculado
desde date_utils.today_in_argentina -- no adivinado por el LLM ni
hardcodeado en el prompt.

Usa un LLM stub que registra los mensajes recibidos (sin llamar a
ningún LLM real ni requerir API key), y parchea
agent.graph.today_in_argentina para fijar la fecha inyectada.
"""
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from langchain_core.messages import AIMessage


class _RecordingFakeLLM:
    """Stub de chat model: registra los mensajes que recibe y devuelve
    una respuesta fija, sin tool_calls (para que el grafo termine en
    un solo paso, via tools_condition -> END).
    """

    def __init__(self):
        self.received_messages = None

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.received_messages = messages
        return AIMessage(content="ok")


def _system_message_contents(messages) -> list[str]:
    # state["messages"] llega normalizado a BaseMessage por LangGraph,
    # pero los mensajes que arma agent_node (system prompt + contexto
    # de fecha) siguen siendo tuplas (role, content) sin normalizar
    # todavía en el momento en que el stub las recibe. Filtramos por
    # tipo antes de desempaquetar para no romper con los BaseMessage.
    return [item[1] for item in messages if isinstance(item, tuple) and item[0] == "system"]


def test_agent_node_injects_argentina_date_context_from_date_utils():
    fixed_today = date(2026, 9, 21)
    fake_llm = _RecordingFakeLLM()

    with patch("agent.graph.get_llm", return_value=fake_llm), patch(
        "agent.graph.today_in_argentina", return_value=fixed_today
    ):
        from agent.graph import build_graph

        graph = build_graph()
        graph.invoke({"messages": [("user", "hola")]})

    assert fake_llm.received_messages is not None
    system_contents = _system_message_contents(fake_llm.received_messages)
    assert any("2026-09-21" in c for c in system_contents), (
        f"la fecha de Argentina no llegó como mensaje de sistema: {system_contents}"
    )


def test_agent_node_uses_date_utils_result_not_a_fixed_value():
    # Si cambia lo que devuelve today_in_argentina, el contexto cambia
    # con eso: prueba que agent_node no cachea ni hardcodea la fecha,
    # sino que la recalcula desde la fuente determinística en cada llamada.
    fake_llm = _RecordingFakeLLM()

    with patch("agent.graph.get_llm", return_value=fake_llm), patch(
        "agent.graph.today_in_argentina", return_value=date(2031, 12, 25)
    ):
        from agent.graph import build_graph

        graph = build_graph()
        graph.invoke({"messages": [("user", "hola")]})

    system_contents = _system_message_contents(fake_llm.received_messages)
    assert any("2031-12-25" in c for c in system_contents)


def test_agent_node_still_includes_static_system_prompt():
    # El contexto de fecha se suma al system prompt existente, no lo
    # reemplaza.
    from prompts.system_prompt import SYSTEM_PROMPT

    fake_llm = _RecordingFakeLLM()

    with patch("agent.graph.get_llm", return_value=fake_llm), patch(
        "agent.graph.today_in_argentina", return_value=date(2026, 1, 1)
    ):
        from agent.graph import build_graph

        graph = build_graph()
        graph.invoke({"messages": [("user", "hola")]})

    system_contents = _system_message_contents(fake_llm.received_messages)
    assert SYSTEM_PROMPT in system_contents


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
