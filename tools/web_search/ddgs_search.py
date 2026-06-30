"""Web search via DuckDuckGo (ddgs) — free, scraping-based, no API key needed."""

import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from html import unescape

import httpx
import trafilatura
from ddgs import DDGS

from configs.config import settings

_SEARCH_TIMEOUT = 8.0
_PAGE_FETCH_TIMEOUT = 5.0
_OVERALL_TIMEOUT = 15.0


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
        with httpx.Client(timeout=_PAGE_FETCH_TIMEOUT, follow_redirects=True) as client:
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


def _do_search(query: str) -> list[dict]:
    try:
        return list(DDGS().text(
            query,
            max_results=settings.WEB_SEARCH_MAX_RESULTS,
            backend="duckduckgo",
            timeout=int(_SEARCH_TIMEOUT),
        ))
    except TypeError:
        return list(DDGS().text(query, max_results=settings.WEB_SEARCH_MAX_RESULTS))


def search(query: str) -> dict:
    with ThreadPoolExecutor(max_workers=1) as guard:
        future = guard.submit(_search_and_fetch, query)
        try:
            return future.result(timeout=_OVERALL_TIMEOUT)
        except FutureTimeoutError:
            return {"context": "", "sources": []}


def _search_and_fetch(query: str) -> dict:
    try:
        results = _do_search(query)
    except Exception:
        return {"context": "", "sources": []}

    if not results:
        return {"context": "", "sources": []}

    hrefs = [r.get("href", "").strip() for r in results if r.get("href", "").strip()]
    page_contents = {}
    if hrefs:
        with ThreadPoolExecutor(max_workers=min(5, len(hrefs))) as pool:
            try:
                for href, content in zip(hrefs, pool.map(_fetch_page, hrefs, timeout=_PAGE_FETCH_TIMEOUT + 2)):
                    if content:
                        page_contents[href] = content
            except FutureTimeoutError:
                pass

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
