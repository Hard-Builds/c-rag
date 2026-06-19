import time

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate
from langchain_core.runnables import RunnableConfig

from app.bot import RAGState
from app.bot.llm import llm_model, str_parser
from app.constants.enums import MessageRoleEnum
from app.core import logger
from app.db.services import MessageService


async def chat_bot(state: RAGState, config: RunnableConfig) -> dict:
    context = state.get("context") or list()

    context_chunk = ""
    if context:
        logger.info("Proceeding with context...")
        context_chunk = "\n".join([
            f"[{idx + 1}]. {chunk.page_content}"
            for idx, chunk in enumerate(context)
        ])
        prompt_message_list = [
            SystemMessage(
                content="You are a helpful assistant. When relevant context is provided, "
                        "use it to answer the user's question accurately. If no context "
                        "is provided or the question is unrelated to the context, answer "
                        "naturally from your own knowledge.\n"
                        f"Conversation Summary: {state.get("summary", "")}"
            ),
            *state["messages"],
            HumanMessagePromptTemplate.from_template(
                template="Context: {context}\n"
                         "Question: {question}"
            )
        ]
    else:
        logger.info("Proceeding without context...")
        prompt_message_list = [
            SystemMessage(
                content="You are a helpful assistant."
                        f"Conversation Summary: {state.get("summary", "")}"
            ),
            *state["messages"],
            HumanMessagePromptTemplate.from_template(
                template="Question: {question}"
            )
        ]

    prompt = ChatPromptTemplate.from_messages(prompt_message_list)
    chain = prompt | llm_model

    start = time.monotonic()

    answer_chunks = []
    full_response = None
    async for event in chain.astream_events({
        "question": state["question"],
        "context": context_chunk
    }):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                chunk_content = await str_parser.ainvoke(chunk)
                answer_chunks.append(chunk_content)
                # Push token to the stream queue
                queue = config["configurable"].get("stream_queue")
                if queue:
                    await queue.put(chunk_content)

        elif event["event"] == "on_chat_model_end":
            full_response = event["data"]["output"]

    latency_ms = int((time.monotonic() - start) * 1000)
    answer_str = "".join(answer_chunks)

    # Signal Streaming is done
    if queue := config["configurable"].get("stream_queue"):
        await queue.put(None)

    # Storing the messages
    db = config["configurable"]["db"]
    thread_id = config["configurable"]["thread_id"]

    msg_service = MessageService(db)

    metadata = {}
    if full_response and hasattr(full_response, "usage_metadata"):
        metadata = full_response.usage_metadata or {}

    # Human message
    _ = await msg_service.create({
        "thread_id": thread_id,
        "role": MessageRoleEnum.HUMAN,
        "content": state["question"],
        "token_count": metadata.get("input_tokens")
    })

    # AI message
    _ = await msg_service.create({
        "thread_id": thread_id,
        "role": MessageRoleEnum.AI,
        "content": answer_str,
        "token_count": metadata.get("output_tokens"),
        "latency_ms": latency_ms
    })

    return {
        "answer": answer_str,
        "context": [],
        "messages": [HumanMessage(state["question"]), AIMessage(answer_str)]
    }
