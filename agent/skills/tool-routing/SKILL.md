---
name: tool-routing
description: Decide whether a request needs internal RAG, live web research, private journal search, multiple tools, or no retrieval tool.
---

# Tool Routing

Choose tools from the user's intent. There is no mandatory tool order and no automatic fallback chain.

## Available evidence sources

- Use `rag_search` for indexed internal documents, uploaded files, policies, or organization-specific knowledge.
- Use `live_web_search` for current, external, public, or time-sensitive information.
- Use `journal_search` only for personal journal entries belonging to the current user.
- Use multiple tools when the request explicitly requires comparison or synthesis across evidence sources.
- Use no retrieval tool for conversational requests that can be answered without factual retrieval.

## Routing rules

1. Infer the evidence source from the request, not from keyword matching alone.
2. Call only tools that can materially improve the answer.
3. A low-confidence or empty result is evidence about that source, not an instruction to call another tool.
4. Never search the private journal for a general knowledge question.
5. Preserve source URLs and document names exactly as returned by tools.
