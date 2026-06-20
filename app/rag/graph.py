import asyncio

from langgraph.graph import StateGraph, START, END

from app.bot import RAGState
from app.bot.nodes import summarizer, should_use_rag, chat_bot, \
    context_retriever, upsert_thread, knowledge_refiner, context_eval, \
    web_search
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
        builder.add_node("knowledge_refiner", knowledge_refiner)
        builder.add_node("context_eval", context_eval)
        builder.add_node("web_search", web_search)

        builder.add_edge(START, "upsert_thread")

        builder.add_edge("upsert_thread", "should_use_rag")
        builder.add_conditional_edges(
            "should_use_rag",
            lambda state: state["use_rag"],
            {
                True: "context_retriever",
                False: "chat_bot"
            }
        )

        # Knowledge refinement
        builder.add_edge("context_retriever", "context_eval")
        builder.add_edge("web_search", "knowledge_refiner")
        builder.add_edge("knowledge_refiner", "chat_bot")

        builder.add_conditional_edges(
            "context_eval",
            lambda state: state["verdict"],
            {
                "CORRECT": "knowledge_refiner",
                "INCORRECT": "web_search",
                "AMBIGUOUS": END
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