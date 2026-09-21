"""Definición del grafo del agente con LangGraph.

V1: el flujo más simple posible.

    agent --(tool_call?)--> tools --> agent --(no tool_call)--> END

El estado es MessagesState (solo la lista de mensajes de la conversación).
Cuando sumemos memoria/estado diario, esto crecerá a un estado custom.
"""
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from config import get_llm
from date_utils import today_in_argentina
from prompts.system_prompt import SYSTEM_PROMPT
from tools import TOOLS


def build_graph():
    llm = get_llm().bind_tools(TOOLS)

    def agent_node(state: MessagesState):
        date_context = (
            "system",
            f"Fecha actual (Argentina): {today_in_argentina().isoformat()}.",
        )
        messages = [("system", SYSTEM_PROMPT), date_context] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile()
