"""Web search tool: searches the web via DuckDuckGo with page content extraction."""

import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape

import httpx
import trafilatura
from ddgs import DDGS

from tools.base import BaseTool, ToolDefinition, ToolResult
from configs.config import settings


def _extract_text_from_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\\1>", " ", html)
    html = re.sub(r"(?is)<br\\s*/?>", "\n", html)
    html = re.sub(r"(?is)</p\\s*>", "\n", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = unescape(html)
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n{2,}", "\n", html)
    return html.strip()


def _fetch_page(url: str) -> str:
    try:
        with httpx.Client(timeout=6.0, follow_redirects=True) as client:
            resp = client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            resp.raise_for_status()
    except Exception:
        return ""
    try:
        text = trafilatura.extract(resp.text) or _extract_text_from_html(resp.text)
    except Exception:
        text = _extract_text_from_html(resp.text)
    return (text or "")[:4000]


def web_search(query: str) -> dict:
    try:
        results = list(DDGS().text(query, max_results=settings.WEB_SEARCH_MAX_RESULTS))
    except Exception:
        return {"context": "", "sources": []}

    hrefs = [r.get("href", "").strip() for r in results]
    page_contents = {}
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(hrefs)))) as pool:
        for href, content in zip(hrefs, pool.map(_fetch_page, hrefs)):
            if href:
                page_contents[href] = content

    texts, sources = [], []
    for r in results:
        title = r.get("title", "").strip()
        body = r.get("body", "").strip()
        href = r.get("href", "").strip()
        if href:
            sources.append(href)
        parts = []
        if title:
            parts.append(f"Title: {title}")
        if body:
            parts.append(f"Snippet: {body}")
        page = page_contents.get(href, "")
        if page:
            parts.append(f"Page Content: {page}")
        if parts:
            texts.append("\n".join(parts))

    return {"context": "\n\n".join(texts), "sources": sources}


class WebTool(BaseTool):
    definition = ToolDefinition(
        name="web",
        description="Search the web for current/recent information",
    )

    def execute(self, user_id: str, query: str = "", **kwargs) -> ToolResult:
        try:
            result = web_search(query)
            context = result.get("context", "")
            sources = result.get("sources", [])
            if not context:
                return ToolResult(context="No web results found.", sources=[])
            return ToolResult(context=context, sources=sources)
        except Exception as e:
            return ToolResult(error=f"Web search failed: {e}")
