"""Shared helpers used by both sqlite and supabase journal_repo.py
(identical logic in both backends — kept here instead of duplicated)."""

import json
import logging

logger = logging.getLogger(__name__)


def safe_embed(text: str) -> str:
    try:
        from rag.embeddings import embed_query
        return json.dumps(embed_query(text).tolist())
    except ImportError:
        logger.debug("sentence_transformers not available — skipping embeddings")
        return "[]"


def build_search_text(title, content, mood, tags) -> str:
    tag_str = " ".join(tags) if tags else ""
    return "\n".join(p for p in [title or "", content or "", mood or "", tag_str] if p)
