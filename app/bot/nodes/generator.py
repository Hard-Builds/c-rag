import time

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate
from langchain_core.runnables import RunnableConfig

from app.bot import RAGState
from app.bot.llm import llm_model, str_parser
from app.constants.enums import MessageRoleEnum
from app.db.services import MessageService


async def chat_bot(state: RAGState, config: RunnableConfig) -> dict:
    context = state.get("context") or list()

    context_chunk = ""
    if context:
        print("Proceeding with context...")
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
        print("Proceeding without context...")
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
    ai_msg = await chain.ainvoke({
        "question": state["question"],
        "context": context_chunk
    })
    latency_ms = int((time.monotonic() - start) * 1000)

    # Storing the messages
    db = config["configurable"]["db"]
    thread_id = config["configurable"]["thread_id"]
    metadata = ai_msg.usage_metadata or {}

    msg_service = MessageService(db)

    # Human message
    _ = await msg_service.create({
        "thread_id": thread_id,
        "role": MessageRoleEnum.HUMAN,
        "content": state["question"],
        "token_count": metadata.get("input_tokens")
    })

    # AI message
    answer_str = await str_parser.ainvoke(ai_msg)
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
        "messages": [HumanMessage(state["question"]), ai_msg]
    }
