from embeddings.sentence_embeddings import embed_query
from retrieval.vector_store import VectorStore

store = VectorStore.load("storage")


def search_documents(query: str):
    query_vector = embed_query(query)
    results = store.search(query_vector, k=3)

    context = "\n".join(
        r["document"]["content"] for r in results
    )

    return context
