"""RAG tool: searches the user's uploaded documents via hybrid search + reranking."""

from tools.base import BaseTool, ToolDefinition, ToolResult
from configs.config import settings

_SUMMARY_TERMS = ("summarize", "summary", "overview", "key points", "main points")
_DOC_SCOPE_TERMS = ("uploaded", "upload", "document", "documents", "file", "files", "knowledge base", "kb")


def _get_store():
    try:
        from retrieval.vector_store import VectorStore
        return VectorStore.load(settings.STORAGE_DIR)
    except Exception:
        return None


def _format_docs(documents: list[dict]) -> str:
    blocks = []
    for i, doc in enumerate(documents, 1):
        source = str(doc.get("source", "unknown"))
        content = str(doc.get("content", "")).strip()
        if content:
            blocks.append(f"[Document {i} | Source: {source}]\n{content}")
    return "\n\n".join(blocks)


def _unique_sources(documents: list[dict]) -> list[str]:
    seen = set()
    sources = []
    for doc in documents:
        s = str(doc.get("source", "unknown"))
        if s not in seen:
            sources.append(s)
            seen.add(s)
    return sources


def hybrid_search_documents(query: str) -> tuple[str, list[str], bool]:
    """Run hybrid search + reranking. Returns (context, sources, should_fallback)."""
    store = _get_store()
    if store is None:
        return "", [], True

    q = query.lower()
    is_summary = (
        any(t in q for t in _SUMMARY_TERMS)
        and any(t in q for t in _DOC_SCOPE_TERMS)
    )

    if is_summary:
        documents = store.documents or []
        if not documents:
            return "", [], True
        if "upload" in q:
            latest_src = str(documents[-1].get("source", ""))
            scoped = [d for d in documents if str(d.get("source", "")) == latest_src]
        else:
            scoped = documents
        top_docs = scoped[:settings.RERANK_K]
        return _format_docs(top_docs), _unique_sources(top_docs), False

    from embeddings.sentence_embeddings import embed_query
    query_vector = embed_query(query)
    results = store.hybrid_search(query, query_vector, k=settings.HYBRID_K)
    strong = [r for r in results if r["score"] >= settings.MIN_HYBRID_SCORE]
    if not strong:
        return "", [], True

    docs = [r["document"] for r in strong]
    from ranker.cross_encoder import rerank_with_scores
    reranked = rerank_with_scores(query, docs)
    top_docs = [r["document"] for r in reranked if r["score"] >= settings.MIN_RERANK_SCORE][:settings.RERANK_K]
    if not top_docs:
        return "", [], True

    return _format_docs(top_docs), [d["source"] for d in top_docs], False


class RagTool(BaseTool):
    definition = ToolDefinition(
        name="rag",
        description="Search the user's uploaded documents and knowledge base",
    )

    def execute(self, user_id: str, query: str = "", **kwargs) -> ToolResult:
        try:
            context, sources, should_fallback = hybrid_search_documents(query)
            if should_fallback or not context:
                return ToolResult(
                    context="No relevant documents found in the knowledge base.",
                    sources=[],
                )
            return ToolResult(context=context, sources=sources)
        except Exception as e:
            return ToolResult(error=f"RAG search failed: {e}")
