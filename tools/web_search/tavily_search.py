"""Web search via Tavily API — paid/freemium, built for AI agents, returns clean content."""

import logging
import time

from configs.config import settings

logger = logging.getLogger(__name__)

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
        logger.warning("Tavily search skipped — TAVILY_API_KEY not set")
        return {"context": "", "sources": []}

    logger.info(f"Tavily search started: query={query!r}")
    start = time.monotonic()

    try:
        client = _get_client()
        response = client.search(
            query=query,
            max_results=settings.WEB_SEARCH_MAX_RESULTS,
            search_depth="basic",
            include_answer=False,
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error(f"Tavily search failed after {elapsed:.2f}s: {e}", exc_info=True)
        return {"context": "", "sources": []}

    elapsed = time.monotonic() - start
    results = response.get("results", [])
    logger.info(f"Tavily search completed in {elapsed:.2f}s — {len(results)} results")

    if not results:
        logger.warning(f"Tavily returned zero results for query={query!r}")
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

    logger.info(f"Tavily search returning {len(sources)} sources, {sum(len(t) for t in texts)} chars of context")
    return {"context": "\n\n".join(texts), "sources": sources}
