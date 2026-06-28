"""All prompt templates for the AI personal assistant."""

SYSTEM_PROMPT = """You are a helpful AI personal assistant. You have access to tools that let you:
- Search a knowledge base of documents the user has uploaded
- Search the web for current information
- Manage the user's journal entries
- Manage tasks and reminders
- Remember facts about the user across conversations
- Manage calendar events

Be concise and helpful. When you use information from tools, cite your sources.
When the user shares personal preferences or facts about themselves, remember them for future conversations.
"""

ROUTER_PROMPT = """Given the user's message, decide which tool to use. Respond with ONLY a JSON object.

Available tools:
- "rag": Search the user's uploaded documents/knowledge base
- "web": Search the web for current/recent information
- "journal": Create, search, or manage journal entries
- "task": Create, list, or manage tasks and reminders
- "memory": Store or recall facts about the user
- "calendar": Create or check calendar events
- "direct": Answer directly without any tool (for greetings, general knowledge, simple questions)

Rules:
- Use "rag" for questions about uploaded documents or internal knowledge
- Use "web" for current events, news, weather, stock prices, or anything time-sensitive
- Use "journal" when the user mentions journal, diary, notes, or reflection
- Use "task" when the user mentions tasks, todos, reminders, or deadlines
- Use "memory" when the user shares a personal fact or asks you to remember something
- Use "calendar" when the user mentions events, meetings, schedules
- Use "direct" for greetings, chitchat, general knowledge, or simple questions

User message: {question}

Respond with: {{"tool": "<tool_name>", "reason": "<brief reason>"}}"""

ANSWER_PROMPT = """Answer the user's question using the provided context. Be concise and accurate.

Context:
{context}

User question: {question}

Rules:
- Only use information from the provided context
- If the context doesn't contain enough information, say so
- Be concise — don't repeat the context back verbatim
- Cite sources when available"""

WEB_ANSWER_PROMPT = """Answer the user's question using the web search results below. Be concise and accurate.

Web results:
{context}

User question: {question}

Rules:
- Synthesize information from the search results
- Cite source URLs when referencing specific information
- If the results don't fully answer the question, say what's missing
- Be concise"""

TOOL_ARGS_PROMPT = """Extract the action and parameters from the user's message for the "{tool}" tool.

Tool: {tool}
User message: {question}

{tool_schema}

Respond with ONLY a valid JSON object containing the extracted parameters."""

TOOL_SCHEMAS = {
    "task": """Parameters:
- "action": "create" | "list" | "complete" | "delete" (required)
- "title": string (required for create)
- "description": string (optional)
- "due_date": "YYYY-MM-DD" (optional)
- "priority": "low" | "medium" | "high" (default: "medium")
- "task_id": string (required for complete/delete)
- "status": "pending" | "in_progress" | "done" (optional filter for list)

Examples:
"Create a task to buy groceries" → {{"action": "create", "title": "Buy groceries"}}
"Remind me to call mom by Friday" → {{"action": "create", "title": "Call mom", "due_date": "2025-01-10", "priority": "high"}}
"Show my tasks" → {{"action": "list"}}
"What are my pending tasks?" → {{"action": "list", "status": "pending"}}""",

    "journal": """Parameters:
- "action": "create" | "search" | "list" (required)
- "query": string (required for search)
- "title": string (optional for create)
- "content": string (required for create)
- "mood": string (optional for create)

Examples:
"Write a journal entry about my productive day" → {{"action": "create", "title": "Productive day", "content": "Had a very productive day today.", "mood": "happy"}}
"Search my journal for meetings" → {{"action": "search", "query": "meetings"}}
"Show my recent journal entries" → {{"action": "list"}}""",

    "memory": """Parameters:
- "action": "store" | "recall" | "list" | "forget" (required)
- "key": string (required for store/forget)
- "value": string (required for store)
- "category": "preference" | "personal" | "work" | "general" (default: "general")
- "query": string (required for recall)

Examples:
"Remember that I prefer dark mode" → {{"action": "store", "key": "ui_preference", "value": "dark mode", "category": "preference"}}
"What do you know about me?" → {{"action": "list"}}
"Do you remember my favorite language?" → {{"action": "recall", "query": "favorite language"}}""",

    "calendar": """Parameters:
- "action": "create" | "list" | "delete" (required)
- "title": string (required for create)
- "start_time": "YYYY-MM-DD HH:MM" or "YYYY-MM-DD" (required for create)
- "end_time": "YYYY-MM-DD HH:MM" (optional)
- "description": string (optional)
- "event_id": string (required for delete)

Examples:
"Schedule a meeting tomorrow at 3pm" → {{"action": "create", "title": "Meeting", "start_time": "2025-01-10 15:00"}}
"What's on my calendar?" → {{"action": "list"}}""",
}

MEMORY_EXTRACTION_PROMPT = """Extract any personal facts the user shared that are worth remembering for future conversations.

User message: {user_message}
Assistant response: {assistant_response}

If the user shared personal facts (name, preferences, job, location, habits, etc.), list them as key-value pairs.
If no memorable facts were shared, respond with "NONE".

Respond with ONLY a JSON array of objects, or "NONE":
[{{"key": "preferred_language", "value": "Python", "category": "preference"}}]"""
