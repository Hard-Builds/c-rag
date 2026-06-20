import asyncio
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
        keep: bool

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
            "You are a strict relevance filter.\n"
            "Return keep=true only if the sentence directly helps answer the question.\n"
            "Use ONLY the sentence. Output JSON only."
        ),
        HumanMessagePromptTemplate.from_template(
            template="Question: {question}\n\n Sentence:{sentence}",
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
    decisions = await asyncio.gather(*[
        filter_chain.ainvoke({
            "question": question,
            "sentence": strips[idx]
        })
        for idx in range(len(strips))
    ])

    kept = [
        strip for strip, d in zip(strips, decisions) if d.keep
    ]

    logger.info(f"Refined and Kept {len(kept)} sentences out of {len(strips)}")

    # 3. Recompose
    refined_context = "\n-".join(kept).strip()

    return {
        "refined_context": refined_context
    }
