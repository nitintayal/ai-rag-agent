from ddgs import DDGS
from configs.config import settings

def web_search_tool(query):
    print("\n🧠 Tool selected: Web Search")
    results = DDGS().text(query, max_results=settings.WEB_SEARCH_MAX_RESULTS)

    texts = []
    sources = []
    for r in results:
        title = r.get("title", "").strip()
        body = r.get("body", "").strip()
        href = r.get("href", "").strip()

        if href:
            sources.append(href)

        parts = []
        if title:
            parts.append(f"Title: {title}")
        if href:
            parts.append(f"URL: {href}")
        if body:
            parts.append(f"Snippet: {body}")

        if parts:
            texts.append("\n".join(parts))

    return {
        "context": "\n\n".join(texts),
        "sources": sources,
    }
