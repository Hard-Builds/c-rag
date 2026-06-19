import asyncio

from langgraph.graph import StateGraph, START, END

from app.bot import RAGState
from app.bot.nodes import summarizer, should_use_rag, chat_bot, \
    context_retriever, upsert_thread
from app.core import settings


class RAGGraph:
    _graph = None
    _lock = asyncio.Lock()

    @classmethod
    async def init(cls, checkpointer):
        async with cls._lock:
            if cls._graph is None:
                cls._graph = await cls._build(checkpointer=checkpointer)
        return cls._graph

    @classmethod
    async def _build(cls, checkpointer):
        builder = StateGraph(RAGState)

        builder.add_node("upsert_thread", upsert_thread)
        builder.add_node("should_use_rag", should_use_rag)
        builder.add_node("context_retriever", context_retriever)
        builder.add_node("chat_bot", chat_bot)
        builder.add_node("summarizer", summarizer)

        builder.add_edge(START, "upsert_thread")
        builder.add_edge("upsert_thread", "should_use_rag")
        builder.add_edge("context_retriever", "chat_bot")
        builder.add_conditional_edges(
            "should_use_rag",
            lambda state: state["use_rag"],
            {
                True: "context_retriever",
                False: "chat_bot"
            }
        )
        builder.add_conditional_edges(
            "chat_bot",
            lambda state: len(state["messages"]) > settings.MAX_CHAT_HISTORY,
            {
                True: "summarizer",
                False: END
            }
        )

        graph = builder.compile(checkpointer=checkpointer)
        return graph