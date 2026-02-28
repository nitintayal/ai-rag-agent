from fastapi import FastAPI
from pydantic import BaseModel

from embeddings.sentence_embeddings import embed_query
from retrieval.vector_store import VectorStore
from agent.local_llm_answer import answer_with_llm
from agent.agent_executor import run_agent
app = FastAPI(title="Local RAG API")

# Load vector store once at startup
store = VectorStore.load("storage")

class QuestionRequest(BaseModel):
    question: str

@app.post("/ask-old")
def ask_question(req: QuestionRequest):
    question = req.question
    query_vector = embed_query(question)
    results = store.search(query_vector, k=3)
    print("Search results:", results)
    context = "\n\n".join(
        f"[Source: {r['document']['source']}]\n{r['document']['content']}"
        for r in results
    )

    answer = answer_with_llm(question, context)

    sources = sorted(set(str(r["document"]["source"]) for r in results))
    avg_confidence = sum(r["score"] for r in results) / len(results)

    return {
        "question": question,
        "answer": answer,
        "confidence": round(avg_confidence * 100, 2),
        "sources": sources
    }



@app.post("/ask")
def ask_question(req: QuestionRequest):

    answer = run_agent(req.question)

    return {"answer": answer}
# {
#   "question": "How often should passwords be changed?"
# }
