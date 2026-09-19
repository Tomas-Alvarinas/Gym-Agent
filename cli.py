"""Interfaz de chat por terminal para Gym Agent.

Mantiene el historial de mensajes en memoria durante la sesión
(sin persistencia todavía: eso llega con la memoria/estado persistente).
"""
from agent.graph import build_graph


def extract_text(message) -> str:
    """Extrae solo el texto visible del content de un AIMessage.

    content puede ser un string simple, o (con Gemini) una lista de
    content blocks como [{"type": "text", "text": "...", "extras": {...}}].
    Se concatena únicamente el texto de los bloques type == "text";
    cualquier otro dato (extras, signature, metadata de tools, etc.) se
    ignora acá pero no se toca message.content, que queda intacto.
    """
    content = message.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)

    return str(content)


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
        print(f"Gym Agent: {extract_text(last_message)}\n")


if __name__ == "__main__":
    main()
