from embeddings.sentence_embeddings import embed_query
from retrieval.vector_store import VectorStore
from ranker.cross_encoder import rerank_with_scores
from configs.config import settings

SUMMARY_INTENT_TERMS = ("summarize", "summary", "overview", "key points", "main points")
DOCUMENT_SCOPE_TERMS = (
    "uploaded",
    "upload",
    "document",
    "documents",
    "file",
    "files",
    "knowledge base",
    "kb",
)


def get_store():
    try:
        return VectorStore.load(settings.STORAGE_DIR)
    except Exception as exc:
        print(f"RAG store unavailable: {exc}")
        return None


def is_document_summary_query(query: str) -> bool:
    normalized = query.lower()
    return (
        any(term in normalized for term in SUMMARY_INTENT_TERMS)
        and any(term in normalized for term in DOCUMENT_SCOPE_TERMS)
    )


def get_source(document):
    return str(document.get("source", "unknown"))


def unique_sources(documents):
    sources = []
    seen = set()
    for document in documents:
        source = get_source(document)
        if source not in seen:
            sources.append(source)
            seen.add(source)
    return sources


def get_summary_documents(store, query: str):
    documents = store.documents or []
    if not documents:
        return []

    normalized = query.lower()
    if "upload" in normalized:
        latest_source = get_source(documents[-1])
        scoped_documents = [
            document for document in documents
            if get_source(document) == latest_source
        ]
    else:
        scoped_documents = documents

    return scoped_documents[:settings.RERANK_K]


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

    if is_document_summary_query(query):
        top_docs = get_summary_documents(store, query)
        if not top_docs:
            return "", [], True

        context = format_documents_as_context(top_docs)
        sources = unique_sources(top_docs)
        return context, sources, False

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
