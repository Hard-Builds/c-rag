from langchain_core.runnables import RunnableConfig

from app.bot import RAGState
from app.bot.llm import llm_model, str_parser
from app.db.services import ThreadService


async def upsert_thread(state: RAGState, config: RunnableConfig):
    config_data = config["configurable"]

    thread_service = ThreadService(config_data["db"])
    thread = await thread_service.get_by_id(config_data["thread_id"])
    if thread is not None:
        return {}

    thread_title_prompt = (
        "You are a helpful assistant, considering the "
        "given query give this thread a short and adequate title that "
        "summarise the intention behind the conversation\n"
        f"Query: {state["question"]}"
    )
    thread_title = await llm_model.ainvoke(thread_title_prompt)
    thread_title_str = await str_parser.ainvoke(thread_title)

    _ = await thread_service.create({
        "id": config_data["thread_id"],
        "user_id": config_data["user_id"],
        "title": thread_title_str
    }, commit=False)
    return {}
