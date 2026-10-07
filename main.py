import asyncio
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph

from graph import build_graph

DB_PATH = "checkpoints.db"
TRACE_PATH = Path("traces/react_trace.json")
RECURSION_LIMIT = 10

CONVERSATION = [
    ("recipes-demo", "¿Qué necesito para la receta más rápida con pollo?"),
    ("recipes-demo", "¿Y la segunda más rápida?"),
    ("dragon-demo", "Quiero una receta con dragón"),
]


def to_trace_step(message: AnyMessage) -> dict[str, Any]:
    step: dict[str, Any] = {"type": message.type, "content": message.content}
    if message.type == "ai" and message.tool_calls:
        step["tool_calls"] = [
            {"name": call["name"], "args": call["args"]} for call in message.tool_calls
        ]
    if message.type == "tool":
        step["tool_name"] = message.name
    return step


async def ask(graph: CompiledStateGraph, thread_id: str, question: str) -> list[dict[str, Any]]:
    config: RunnableConfig = {
        "recursion_limit": RECURSION_LIMIT,
        "configurable": {"thread_id": thread_id},
    }
    previous_state = await graph.aget_state(config)
    already_stored = len(previous_state.values.get("messages", []))
    try:
        result = await graph.ainvoke({"messages": [("user", question)]}, config=config)
    except GraphRecursionError:
        return [{"type": "error", "content": f"Stopped after {RECURSION_LIMIT} steps."}]
    return [to_trace_step(message) for message in result["messages"][already_stored:]]


def print_steps(thread_id: str, steps: list[dict[str, Any]]) -> None:
    print(f"\n[thread_id={thread_id}]")
    for step in steps:
        match step["type"]:
            case "human":
                print(f"User: {step['content']}")
            case "ai" if "tool_calls" in step:
                for call in step["tool_calls"]:
                    print(f"  -> Agent calls {call['name']}({call['args']})")
            case "tool":
                print(f"  <- {step['tool_name']} returned: {step['content']}")
            case "ai":
                print(f"Answer: {step['content']}")
            case "error":
                print(f"Error: {step['content']}")


async def main() -> None:
    load_dotenv()
    TRACE_PATH.parent.mkdir(exist_ok=True)
    trace: list[dict[str, Any]] = []
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        graph = build_graph(checkpointer)
        for thread_id, question in CONVERSATION:
            steps = await ask(graph, thread_id, question)
            print_steps(thread_id, steps)
            trace.append({"thread_id": thread_id, "question": question, "steps": steps})
    TRACE_PATH.write_text(json.dumps(trace, indent=2, ensure_ascii=False))
    print(f"\nTrace saved to {TRACE_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
