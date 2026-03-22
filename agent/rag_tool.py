from embeddings.sentence_embeddings import embed_query
from retrieval.vector_store import VectorStore
from ranker.cross_encoder import rerank

store = VectorStore.load("storage")


def search_documents(query: str):
    query_vector = embed_query(query)
    results = store.search(query_vector, k=3)

    context = "\n".join(
        r["document"]["content"] for r in results
    )

    sources = [r["document"]["source"] for r in results]

    return context, sources

def hybrid_search_documents(query: str):
    query_vector = embed_query(query)
    results = store.hybrid_search(query, query_vector, k=20)

    # Extract docs
    docs = [r["document"] for r in results]

    reranked_docs = rerank(query, docs)

    # Step 3: Take top-k
    top_docs = reranked_docs[:5]


    context = "\n".join(
        r["content"] for r in top_docs
    )

    sources = [r["source"] for r in top_docs]

    return context, sources
