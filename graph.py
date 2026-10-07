import os

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from tools import get_recipe_details, search_recipes

TOOLS = [search_recipes, get_recipe_details]

SYSTEM_PROMPT = SystemMessage(
    "You are a cooking assistant. Answer only with data returned by the tools, "
    "never from your own knowledge. If a tool returns an error, retry once with "
    "a corrected argument; if it still fails, ask the user for clarification. "
    "Always reply in the user's language."
)


class AgentState(MessagesState):
    pass


def build_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0
    ).bind_tools(TOOLS)

    async def call_model(state: AgentState) -> dict[str, list[AnyMessage]]:
        response = await llm.ainvoke([SYSTEM_PROMPT, *state["messages"]])
        return {"messages": [response]}

    builder = StateGraph(AgentState)
    builder.add_node("model", call_model)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", tools_condition)
    builder.add_edge("tools", "model")
    return builder.compile(checkpointer=checkpointer)
