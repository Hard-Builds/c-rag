from langchain_community.tools import TavilySearchResults
from langchain_core.documents import Document

from app.bot import RAGState
from app.core import logger

tavily = TavilySearchResults(max_results=3)


async def web_search(state: RAGState):
    logger.info("Fetching data from web...")
    q = state["question"]
    results = await tavily.ainvoke({"query": q})

    web_docs = []
    for r in results or []:
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content") or r.get("snippet") or ""

        text = (
            f"TITLE: {title}\n"
            f"URL: {url}\n"
            f"CONTENT: \n{content}"
        )
        web_docs.append(Document(
            page_content=text,
            metadata={"url": url, "title": title}
        ))
    return {"web_docs": web_docs}
