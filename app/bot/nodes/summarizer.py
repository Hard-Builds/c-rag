from langchain_core.messages import RemoveMessage
from langchain_core.prompts import ChatPromptTemplate, \
    SystemMessagePromptTemplate

from app.bot import RAGState
from app.bot.llm import llm_model, str_parser


async def summarizer(state: RAGState) -> dict:
    if state.get("summary"):
        prompt = (f"Existing Summary: \n{state["summary"]}\n"
                  f"Extend the summary using the new conversation above")
    else:
        prompt = "Summarize the conversation above"

    prompt = ChatPromptTemplate([
        *state["messages"],
        SystemMessagePromptTemplate.from_template(prompt)
    ])

    chain = prompt | llm_model | str_parser
    summary = await chain.ainvoke({"summary": state.get("summary", "")})
    print("Updating Conversation summary...")

    remove_msgs = [RemoveMessage(id=msg.id) for msg in
                   state["messages"][:-2]]
    return {
        "summary": summary,
        "messages": remove_msgs
    }
