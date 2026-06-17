import os
from typing import List, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, \
    AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, \
    HumanMessagePromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END, MessagesState

from rag_core.retiever import Retriever


class RAGState(MessagesState):
    question: str
    context: List[Document]
    answer: str
    use_rag: bool


class RAGGraph:
    def __init__(self, retriever: Retriever):
        self.retriever = retriever
        self.llm = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL"))
        self.str_parser = StrOutputParser()

    async def _get_chat_history_str(self, state: RAGState) -> str:
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
        return {"context": context}

    async def chat_bot(self, state: RAGState):
        context = state.get("context") or list()

        context_chunk = "\n".join([
            f"[{idx + 1}]. {chunk.page_content}"
            for idx, chunk in enumerate(context)
        ])

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(
                content="You are a helpful assistant. When relevant context is provided, "
                        "use it to answer the user's question accurately. If no context "
                        "is provided or the question is unrelated to the context, answer "
                        "naturally from your own knowledge."
            ),
            *state["messages"],
            HumanMessagePromptTemplate.from_template(
                "Question: {question}\nContext:\n{context}")
        ])
        chain = prompt | self.llm
        ai_msg = await chain.ainvoke({
            "question": state["question"],
            "context": context_chunk
        })
        return {
            "answer": await self.str_parser.ainvoke(ai_msg),
            "messages": [HumanMessage(state["question"]), ai_msg]
        }

    async def build(self, checkpointer):
        builder = StateGraph(RAGState)

        builder.add_node("should_use_rag", self.should_use_rag)
        builder.add_node("context_retriever", self.context_retriever)
        builder.add_node("chat_bot", self.chat_bot)

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
        builder.add_edge("chat_bot", END)

        graph = builder.compile(checkpointer=checkpointer)
        return graph
