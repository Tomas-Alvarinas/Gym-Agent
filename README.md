# Gym Agent

Asistente personal de gimnasio, construido como proyecto de aprendizaje de AI Agents
con Python, LangChain y LangGraph.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# completar ANTHROPIC_API_KEY en .env
```

## Uso

```bash
python cli.py
```

## Estado actual (V1)

- 1 tool: `get_today_workout`
- Rutina ficticia en `data/fixtures/routine.json`
- Grafo LangGraph mínimo: agente ↔ tools
- System prompt en `prompts/system_prompt.py`, editable sin tocar código

## Estructura

```
config.py              # LLM configurable
cli.py                 # chat por terminal
prompts/system_prompt.py
tools/workout_tools.py
data/store.py, data/fixtures/routine.json
agent/graph.py         # definición del grafo
```
