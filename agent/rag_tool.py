from embeddings.sentence_embeddings import embed_query
from retrieval.vector_store import VectorStore
from ranker.cross_encoder import rerank_with_scores
from configs.config import settings


def get_store():
    try:
        return VectorStore.load(settings.STORAGE_DIR)
    except Exception as exc:
        print(f"RAG store unavailable: {exc}")
        return None


def format_documents_as_context(documents):
    blocks = []

    for index, document in enumerate(documents, start=1):
        source = str(document.get("source", "unknown"))
        content = str(document.get("content", "")).strip()

        if not content:
            continue

        blocks.append(
            f"[Document {index} | Source: {source}]\n{content}"
        )

    return "\n\n".join(blocks)

def run_rag(query):
    context, sources, should_fallback = hybrid_search_documents(query)
    return context, sources, should_fallback

def search_documents(query: str):
    store = get_store()
    if store is None:
        return "", []

    query_vector = embed_query(query)
    results = store.search(query_vector, k=3)

    context = "\n".join(
        r["document"]["content"] for r in results
    )

    sources = [r["document"]["source"] for r in results]

    return context, sources

def hybrid_search_documents(query: str):
    store = get_store()
    if store is None:
        return "", [], True

    query_vector = embed_query(query)
    results = store.hybrid_search(query, query_vector, k=settings.HYBRID_K)
    strong_hybrid_results = [
        result for result in results
        if result["score"] >= settings.MIN_HYBRID_SCORE
    ]

    if not strong_hybrid_results:
        return "", [], True

    # Extract docs
    docs = [r["document"] for r in strong_hybrid_results]

    reranked_results = rerank_with_scores(query, docs)
    strong_reranked_results = [
        result for result in reranked_results
        if result["score"] >= settings.MIN_RERANK_SCORE
    ]

    # Step 3: Take top-k
    top_docs = [
        result["document"]
        for result in strong_reranked_results[:settings.RERANK_K]
    ]

    if not top_docs:
        return "", [], True


    context = format_documents_as_context(top_docs)

    sources = [r["source"] for r in top_docs]

    return context, sources, False
