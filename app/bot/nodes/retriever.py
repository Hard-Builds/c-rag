from app.bot import RAGState


async def context_retriever(retriever, state: RAGState):
    question = state["question"]
    context = await retriever.get(question)
    print("Fetching Context...")
    return {"context": context}
