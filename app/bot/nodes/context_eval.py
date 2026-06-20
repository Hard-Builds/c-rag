import asyncio

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, \
    HumanMessagePromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.bot import RAGState
from app.bot.llm import llm_model
from app.core import settings, logger


async def _structured_llm():
    """Returns the LLM bound to structured output schema for chunk relevance scoring."""

    class DocEvalScore(BaseModel):
        score: float = Field(ge=0.0, le=1.0)
        reason: str

    llm_with_model = llm_model.with_structured_output(DocEvalScore)
    return llm_with_model


async def context_eval(state: RAGState, config: RunnableConfig):
    """
    Scores each retrieved chunk against the question and decides whether the
    context is usable for answer generation.

    Verdict logic:
    - CORRECT:   at least one chunk scores above CONTEXT_EVAL_HIGHER_THR → proceed to knowledge_refiner
    - INCORRECT: all chunks score below CONTEXT_EVAL_LOWER_THR → no usable context, answer with fallback
    - AMBIGUOUS: mixed signals, no chunk clears the high bar → answer with fallback
    """
    logger.info("Evaluating Contexts...")

    llm_model = await _structured_llm()
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(
            "You are a strict retrieval evaluator for RAG.\n"
            "You will be given ONE retrieved chunk and a question.\n"
            "Return a relevance score in [0.0, 1.0].\n"
            "- 1.0: chunk alone is sufficient to answer fully/mostly\n"
            "- 0.0: chunk is irrelevant\n"
            "Be conservative with high score.\n"
            "Also return a short reason.\n"
            "Output JSON only."
        ),
        HumanMessagePromptTemplate.from_template(
            "Question: {question}\n\nChunk:\n{chunk}"
        )
    ])

    doc_eval_chain = prompt | llm_model
    context_list = state.get("context", [])

    routines = []
    for chunk in context_list:
        routines.append(
            doc_eval_chain.ainvoke({
                "question": state["question"],
                "chunk": chunk.page_content
            })
        )
    decisions = await asyncio.gather(*routines)

    scores = []
    reasons = []
    good_docs = []
    for decision, context in zip(decisions, context_list):
        scores.append(decision.score)
        reasons.append(decision.reason)
        if decision.score > settings.CONTEXT_EVAL_LOWER_THR:
            good_docs.append(context)

    logger.info(
        f"Approved context chunks: {len(good_docs)}/{len(decisions)}"
    )

    # At least one highly relevant chunk found — proceed to refinement
    if scores and any(s > settings.CONTEXT_EVAL_HIGHER_THR for s in scores):
        return {
            "good_docs": good_docs,
            "verdict": "CORRECT",
            "reason": f"At least one retrieved chunk score > "
                      f"{settings.CONTEXT_EVAL_HIGHER_THR}"
        }

    if scores and all(s < settings.CONTEXT_EVAL_LOWER_THR for s in scores):
        # No chunk clears the minimum bar — nothing useful to pass downstream
        return {
            "good_docs": [],
            "verdict": "INCORRECT",
            "reason": f"All retrieved chunks scored < {settings.CONTEXT_EVAL_LOWER_THR}. "
                      f"No chunk was sufficient.",
        }

    # Some chunks pass the lower bar but none clear the high bar — mixed signals
    return {
        "good_docs": good_docs,
        "verdict": "AMBIGUOUS",
        "reason": f"No chunk scored > {settings.CONTEXT_EVAL_HIGHER_THR},"
                  f"but not all where {settings.CONTEXT_EVAL_LOWER_THR}."
                  f"Mixed relevance signals",
    }