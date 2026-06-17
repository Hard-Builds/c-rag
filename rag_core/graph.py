import os
from typing import List, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, \
    HumanMessagePromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END

from rag_core.retiever import Retriever


class RAGState(TypedDict):
    question: str
    context: List[Document]
    answer: str


class RAGGraph:
    def __init__(self, retriever: Retriever):
        self.retriever = retriever
        self.llm = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL"))
        self.str_parser = StrOutputParser()

    # ------- nodes -------
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
                content="You are a helpful assistant. Answer the user's "
                        "question based on the provided context. If the "
                        "answer is not in the context, say so clearly"
            ),
            HumanMessagePromptTemplate.from_template(
                "Question: {question}\nContext:\n{context}")
        ])
        chain = prompt | self.llm | self.str_parser
        answer = await chain.ainvoke({
            "question": state["question"],
            "context": context_chunk
        })
        return {"answer": answer}

    async def build(self, checkpointer):
        builder = StateGraph(RAGState)

        builder.add_node("context_retriever", self.context_retriever)
        builder.add_node("chat_bot", self.chat_bot)

        builder.add_edge(START, "context_retriever")
        builder.add_edge("context_retriever", "chat_bot")
        builder.add_edge("chat_bot", END)

        graph = builder.compile(checkpointer=checkpointer)
        return graph
