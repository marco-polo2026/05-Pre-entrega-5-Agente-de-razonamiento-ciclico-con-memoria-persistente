# Agente de razonamiento cíclico con memoria persistente

Pre-entrega 5 — AI Engineering, Coderhouse.

Agente de recetas de cocina construido con **LangGraph**. Sigue el ciclo **ReAct**: el LLM
decide por sí mismo cuándo consultar un recetario simulado, lee el resultado y vuelve a
decidir si necesita otra consulta o si ya puede responder. La conversación se guarda en
SQLite por `thread_id`, así que el agente recuerda lo que se habló en la misma sesión.

## Cómo levantar el entorno

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env     # completar OPENAI_API_KEY

python main.py
```

Requiere Python 3.12 o superior (probado con 3.13.3).

`main.py` corre una conversación de prueba, la imprime en consola y guarda la traza en
[`traces/react_trace.json`](traces/react_trace.json).

## Configuración

Las claves viven en `.env`, que está en `.gitignore` y nunca se sube al repositorio.

| Variable | Valor por defecto | Para qué |
|---|---|---|
| `OPENAI_API_KEY` | — | acceso al LLM |
| `OPENAI_MODEL` | `gpt-4o-mini` | modelo de chat |

## Estructura

| Archivo | Qué contiene |
|---|---|
| `tools.py` | Las dos herramientas (`@tool`) y el recetario simulado |
| `graph.py` | El estado, los nodos y las aristas del grafo |
| `main.py` | El checkpointer SQLite, la conversación de prueba y la traza |

## El grafo

```
 START ──► [ model ] ── tools_condition ──► END
              ▲               │
              │               ▼
              └────────── [ tools ]
```

- **`model`**: llama al LLM con las herramientas vinculadas (`bind_tools`).
- **`tools`**: `ToolNode`, ejecuta las herramientas que pidió el LLM.
- **`tools_condition`**: si el último mensaje del LLM pide una herramienta, va a `tools`;
  si no, termina. La decisión la toma el LLM, no hay `if/else` sobre la pregunta.
- El estado (`AgentState`) hereda de `MessagesState`: una lista de mensajes que se acumula
  con el reducer `add_messages`.

## Las herramientas

| Herramienta | Recibe | Devuelve |
|---|---|---|
| `search_recipes` | un ingrediente | id, nombre y minutos de cada receta que lo usa |
| `get_recipe_details` | el id de una receta | ingredientes y pasos |

`search_recipes` no devuelve ingredientes ni pasos a propósito: para responder, el agente
necesita el id que devuelve la primera para poder llamar a la segunda. Eso obliga a un
razonamiento de varios pasos.

Si una herramienta no encuentra nada, no lanza una excepción: devuelve `{"error": ...}`.
El LLM lo lee y puede reintentar con otro argumento o pedirle una aclaración al usuario.

## Traza de ejecución

[`traces/react_trace.json`](traces/react_trace.json) muestra tres casos:

| Pregunta | `thread_id` | Qué demuestra |
|---|---|---|
| ¿Qué necesito para la receta más rápida con pollo? | `recipes-demo` | Dos llamadas encadenadas: `search_recipes("chicken")` y después `get_recipe_details(1)` |
| ¿Y la segunda más rápida? | `recipes-demo` | Memoria: recuerda la lista anterior y llama directo a `get_recipe_details(3)`, sin volver a buscar |
| Quiero una receta con dragón | `dragon-demo` | Error: la herramienta no encuentra nada y el agente pide una aclaración |

## Decisiones

**`AsyncSqliteSaver` en lugar de `SqliteSaver`.** La consigna pide `SqliteSaver` y
`asyncio`. `SqliteSaver` no soporta métodos asíncronos: sus métodos `a*` lanzan
`NotImplementedError` y recomiendan usar `AsyncSqliteSaver`. Es la versión asíncrona del
mismo checkpointer, viene en el mismo paquete (`langgraph-checkpoint-sqlite`) y guarda en
el mismo formato de archivo SQLite.

**`recursion_limit=10` en cada invocación.** En LangGraph 1.2 el límite por defecto es
10007 pasos, que en la práctica equivale a no tener techo. Una pregunta con dos
herramientas usa 5 pasos (`model`, `tools`, `model`, `tools`, `model`); 10 deja margen
para un reintento. Si se supera, se atrapa `GraphRecursionError`.

**Los datos están en un `dict`.** La consigna pide *simular* una base de datos. Pasarlos
a una tabla real solo cambiaría el cuerpo de las herramientas: el nombre, el docstring y
lo que devuelven quedan iguales, y el grafo no se entera.

## Limitaciones

- El estado acumula todos los mensajes de un `thread_id`. En conversaciones largas
  habría que recortar o resumir los mensajes viejos para no superar el contexto del modelo.
- `checkpoints.db` está en `.gitignore`: cada clon arranca sin memoria previa.
