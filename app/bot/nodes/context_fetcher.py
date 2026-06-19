from langchain_core.runnables import RunnableConfig

from app.bot import RAGState
from app.core import logger
from app.rag.retriever import Retriever

async def context_retriever(state: RAGState, config: RunnableConfig) -> dict:
    config_dict = config["configurable"]
    context = await Retriever.get(
        db=config_dict["db"],
        user_id=config_dict["user_id"],
        query=state["question"]
    )
    logger.info("Fetching Context...")
    return {"context": context}
