"""Safe embedding helper — returns empty list if ML libs aren't installed."""

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
