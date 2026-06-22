import re

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, \
    HumanMessagePromptTemplate
from pydantic import BaseModel

from app.bot import RAGState
from app.bot.llm import llm_model
from app.core import logger


async def _structured_llm():
    class KeepOrDrop(BaseModel):
        kept: list[str]

    llm_with_model = llm_model.with_structured_output(KeepOrDrop)
    return llm_with_model


async def _decompose_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


async def knowledge_refiner(state: RAGState):
    """
    Refines the retrieved context, to remove the unnecessary chunks of data,
    this can help with the answer generation quality
    Steps:
    1. Decomposition
    2. Filtration
    3. Recomposition
    """
    llm_model = await _structured_llm()

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(
            "You are a strict relevance filter for a RAG pipeline.\n"
            "Given a question and a numbered list of sentences, decide which sentences directly and specifically answer the question.\n\n"
            "Rules: \n"
            "- Keep the sentence ONLY if it contains information that directly addresses the question.\n"
            "- Drop sentence that are generic, off-topic, or only loosely related.\n"
            "- DO NOT modify, rephrase or merge sentences.\n"
            "- Return a JSON object with a single key 'kept' stating the list of sentences to keep.\n"
            "- If no sentence is relevant, return an empty list."
        ),
        HumanMessagePromptTemplate.from_template(
            template="Question: {question}\n\n "
                     "Sentences:\n{sentences}\n\n"
                     "Return only the JSON",
        )
    ])
    filter_chain = prompt | llm_model

    question = state["question"]

    if state["verdict"] == "CORRECT":
        logger.info("Refining context...")
        context = state.get("good_docs", [])
    elif state["verdict"] == "INCORRECT":
        logger.info("Refining web docs...")
        context = state.get("web_docs", [])
    elif state["verdict"] == "AMBIGUOUS":
        logger.info("Refining both good and web docs...")
        context = state.get("web_docs", []) + state.get("good_docs", [])

    context_chunk = "\n\n".join([
        f"{chunk.page_content}"
        for idx, chunk in enumerate(context)
    ])

    # 1. Decomposition
    strips = await _decompose_sentences(context_chunk)

    # 2. Filter
    refined_context = await filter_chain.ainvoke({
        "question": question,
        "sentences": "\n".join(map(
            lambda x: f"[{x[0] + 1}]. {x[1]}",
            enumerate(strips)
        ))
    })

    return {
        "refined_context": "\n\n".join(refined_context.kept)
    }
