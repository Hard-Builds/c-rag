from typing import TypedDict

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, \
    AIMessage
from langgraph.graph import MessagesState

from app.bot import RAGState
from app.bot.llm import llm_model, str_parser


async def _get_chat_history_str(state: MessagesState) -> str:
    chat_history = []
    for message in state["messages"]:
        role = ""
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, ToolMessage):
            role = "tool"
        elif isinstance(message, AIMessage):
            role = "AI"

        chat_history.append(
            f"[{role}]: {await str_parser.ainvoke(message)}"
        )

    return "\n".join(chat_history)


async def should_use_rag(state: RAGState) -> dict:
    """This to reduce the possibility of in-descriminant retrieval"""
    class RAGDecisionResp(TypedDict):
        use_rag: bool

    chat_history = await _get_chat_history_str(state)

    prompt = (
        "You are a routing assistant. Decide if the following conversation requires "
        "retrieving information from a document database (RAG) or can be answered "
        "directly from general knowledge or chat history.\n\n"
        "Return use_rag=true if the current query asks about specific documents, files, "
        "or content that would need to be looked up — including follow-up questions "
        "referencing a previous RAG response.\n"
        "Return use_rag=false if the query is casual conversation, a greeting, "
        "or a general knowledge question answerable without documents.\n\n"
        f"Chat History:\n{chat_history}\n\n"
        f"Current Query: {state['question']}"
    )

    response: RAGDecisionResp = await llm_model.with_structured_output(
        RAGDecisionResp).ainvoke(prompt)
    return {"use_rag": response["use_rag"]}
