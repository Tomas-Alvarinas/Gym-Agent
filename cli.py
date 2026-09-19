"""Interfaz de chat por terminal para Gym Agent.

Mantiene el historial de mensajes en memoria durante la sesión
(sin persistencia todavía: eso llega con la memoria/estado persistente).
"""
from agent.graph import build_graph


def main():
    graph = build_graph()
    messages = []

    print("Gym Agent (V1). Escribi 'salir' para terminar.\n")

    while True:
        user_input = input("Vos: ").strip()
        if user_input.lower() in {"salir", "exit", "quit"}:
            break
        if not user_input:
            continue

        messages.append(("user", user_input))
        result = graph.invoke({"messages": messages})
        messages = result["messages"]

        last_message = messages[-1]
        print(f"Gym Agent: {last_message.content}\n")


if __name__ == "__main__":
    main()
