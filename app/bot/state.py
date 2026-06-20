from typing import List

from langchain_core.documents import Document
from langgraph.graph import MessagesState


class RAGState(MessagesState):
    question: str
    answer: str

    use_rag: bool

    # Context Node variables
    context: List[Document]

    # Context Eval
    good_docs: List[Document]
    verdict: str
    reason: str

    # Web search vars
    web_search_query: str
    web_docs: List[Document]

    # Context Refinement Variables
    refined_context: str

    # Summarize node variable
    summary: str  # This helps reducing the llm context window to shortest
