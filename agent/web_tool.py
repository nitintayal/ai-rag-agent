import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape

import httpx
import trafilatura
from ddgs import DDGS

from configs.config import settings


def extract_text_from_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\\1>", " ", html)
    html = re.sub(r"(?is)<br\\s*/?>", "\n", html)
    html = re.sub(r"(?is)</p\\s*>", "\n", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = unescape(html)
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n{2,}", "\n", html)
    return html.strip()


def fetch_page_content(url: str) -> str:
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                },
            )
            response.raise_for_status()
    except Exception as exc:
        print(f"Failed to fetch page content: {exc}")
        return ""

    text = trafilatura.extract(response.text) or extract_text_from_html(response.text)
    return text[:4000]


def web_search_tool(query):
    print("\n🧠 Tool selected: Web Search")
    try:
        results = list(DDGS().text(query, max_results=settings.WEB_SEARCH_MAX_RESULTS))
    except Exception as exc:
        print(f"Web search failed: {exc}")
        return {"context": "", "sources": []}

    hrefs = [r.get("href", "").strip() for r in results]
    page_contents = {}

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(hrefs)))) as executor:
        fetched_pages = executor.map(fetch_page_content, hrefs)
        for href, page_content in zip(hrefs, fetched_pages):
            if href:
                page_contents[href] = page_content

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
        # if href:
        #     parts.append(f"URL: {href}")
        if body:
            parts.append(f"Snippet: {body}")
        if href:
            page_content = page_contents.get(href, "")
            if page_content:
                parts.append(f"Page Content: {page_content}")

        if parts:
            texts.append("\n".join(parts))

    return {
        "context": "\n\n".join(texts),
        "sources": sources,
    }
