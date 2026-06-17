from typing import List

from langchain_core.documents import Document
from langgraph.graph import MessagesState


class RAGState(MessagesState):
    question: str
    context: List[Document]
    answer: str
    use_rag: bool
    summary: str
