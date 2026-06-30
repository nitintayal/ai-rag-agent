"""Web search via Tavily API — paid/freemium, built for AI agents, returns clean content."""

from configs.config import settings

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    from tavily import TavilyClient
    _client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    return _client


def search(query: str) -> dict:
    if not settings.TAVILY_API_KEY:
        return {"context": "", "sources": []}

    try:
        client = _get_client()
        response = client.search(
            query=query,
            max_results=settings.WEB_SEARCH_MAX_RESULTS,
            search_depth="basic",
            include_answer=False,
        )
    except Exception:
        return {"context": "", "sources": []}

    results = response.get("results", [])
    if not results:
        return {"context": "", "sources": []}

    texts, sources = [], []
    for r in results:
        title = r.get("title", "").strip()
        content = r.get("content", "").strip()
        url = r.get("url", "").strip()
        if url:
            sources.append(url)
        parts = []
        if title:
            parts.append(f"Title: {title}")
        if content:
            parts.append(f"Content: {content}")
        if parts:
            texts.append("\n".join(parts))

    return {"context": "\n\n".join(texts), "sources": sources}
