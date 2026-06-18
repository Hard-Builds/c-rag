from typing import TypedDict

from langchain_core.messages import RemoveMessage
from langchain_core.messages import (SystemMessage, HumanMessage,
                                     ToolMessage, AIMessage)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, \
    SystemMessagePromptTemplate
from langchain_core.prompts import HumanMessagePromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END, MessagesState

from app.bot import RAGState
from app.core.config import settings
from app.rag.retriever import Retriever


class RAGGraph:
    def __init__(self, retriever: Retriever, chat_history_len: int = 10):
        self.retriever = retriever
        self.llm = ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL)
        self.str_parser = StrOutputParser()
        self.chat_history_len = chat_history_len

    async def _get_chat_history_str(self, state: MessagesState) -> str:
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
                f"[{role}]: {await self.str_parser.ainvoke(message)}"
            )

        return "\n".join(chat_history)

    async def build(self, checkpointer):
        builder = StateGraph(RAGState)

        builder.add_node("should_use_rag", self.should_use_rag)
        builder.add_node("context_retriever", self.context_retriever)
        builder.add_node("chat_bot", self.chat_bot)
        builder.add_node("summarizer", self.summarizer)

        builder.add_edge(START, "should_use_rag")
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
            lambda state: len(state["messages"]) > self.chat_history_len,
            {
                True: "summarizer",
                False: END
            }
        )

        graph = builder.compile(checkpointer=checkpointer)
        return graph

    # ------- nodes -------
    async def should_use_rag(self, state: RAGState):
        class RAGDecisionResp(TypedDict):
            use_rag: bool

        chat_history = await self._get_chat_history_str(state)

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

        response: RAGDecisionResp = await self.llm.with_structured_output(
            RAGDecisionResp).ainvoke(prompt)
        return {"use_rag": response["use_rag"]}

    async def context_retriever(self, state: RAGState):
        question = state["question"]
        context = await self.retriever.get(question)
        print("Fetching Context...")
        return {"context": context}

    async def chat_bot(self, state: RAGState):
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
        chain = prompt | self.llm
        ai_msg = await chain.ainvoke({
            "question": state["question"],
            "context": context_chunk
        })
        return {
            "answer": await self.str_parser.ainvoke(ai_msg),
            "context": [],
            "messages": [HumanMessage(state["question"]), ai_msg]
        }

    async def summarizer(self, state: RAGState):
        if state.get("summary"):
            prompt = (f"Existing Summary: \n{state["summary"]}\n"
                      f"Extend the summary using the new conversation above")
        else:
            prompt = "Summarize the conversation above"

        prompt = ChatPromptTemplate([
            *state["messages"],
            SystemMessagePromptTemplate.from_template(prompt)
        ])

        chain = prompt | self.llm | self.str_parser
        summary = await chain.ainvoke({"summary": state.get("summary", "")})
        print("Updating Conversation summary...")

        remove_msgs = [RemoveMessage(id=msg.id) for msg in
                       state["messages"][:-2]]
        return {
            "summary": summary,
            "messages": remove_msgs
        }
