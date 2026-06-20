from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel

from app.bot import RAGState
from app.bot.llm import llm_model
from app.core import logger


class WebQuery(BaseModel):
    query: str


async def rewrite_query(state: RAGState):
    logger.info("Rewriting the user query for web search...")
    response = await llm_model.with_structured_output(WebQuery).ainvoke([
        SystemMessage(
            "Rewrite the user question into a web search query composed of keywords.\n"
            "Rules:\n"
            "- Keep it short (6-14 words)\n"
            "- If the question implies recency (e.g., recent/latest/last week/ last month), add a constraint like (like 30 days).\n"
            "- Do NOT answer the question.\n"
            "- Return JSON with a single key: query"
        ),
        HumanMessage(f"Question: {state["question"]}")
    ])
    return {"web_search_query": response.query}
