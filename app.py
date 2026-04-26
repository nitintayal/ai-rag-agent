import inspect
import shutil
from pathlib import Path

import gradio as gr

from agent.agent_executor import run_agent
from agent.local_llm_answer import answer_with_llm
from configs.config import settings
from ingestion.ingest_documents import ingest_documents
from journal.schemas import JournalEntryCreate, JournalEntryUpdate
from journal.factory import get_journal_store


APP_TITLE = "AI RAG Agent"
APP_SUBTITLE = "A ChatGPT-style demo for knowledge-base chat, live web routing, and journal reflection."
DATA_FOLDER = Path(settings.DATA_DIR)
SUPPORTED_UPLOAD_EXTENSIONS = {".txt", ".pdf", ".xlsx"}

INITIAL_ASSISTANT_MESSAGES = [
    {
        "role": "assistant",
        "content": "Ask about your indexed documents, policies, notes, or current topics. I'll route to web search when the question needs fresh information.",
    }
]

INITIAL_JOURNAL_MESSAGES = [
    {
        "role": "assistant",
        "content": "This is your journal copilot. Ask things like 'What patterns do you see this week?' or 'When did I last feel productive?'",
    }
]


def get_chatbot_kwargs():
    try:
        params = inspect.signature(gr.Chatbot.__init__).parameters
    except (TypeError, ValueError):
        return {}, "tuples"

    kwargs = {}
    if "type" in params:
        kwargs["type"] = "messages"
    if "allow_tags" in params:
        kwargs["allow_tags"] = False

    return kwargs, "messages" if "type" in kwargs else "tuples"


CHATBOT_KWARGS, CHATBOT_FORMAT = get_chatbot_kwargs()


def get_safe_journal_store():
    try:
        return get_journal_store()
    except Exception as exc:
        print(f"Journal store unavailable: {exc}")
        return None


def format_sources(sources):
    if not sources:
        return "No sources returned."
    return "\n".join(f"- {source}" for source in sources)


def build_assistant_message(answer, sources):
    return f"{answer}\n\nSources\n{format_sources(sources)}"


def history_to_chatbot_messages(history):
    if CHATBOT_FORMAT == "messages":
        return [
            {"role": turn.get("role"), "content": turn.get("content", "")}
            for turn in history
            if turn.get("role") in {"user", "assistant"}
        ]

    messages = []
    pending_user = None
    for turn in history:
        role = turn.get("role")
        content = turn.get("content", "")
        if role == "user":
            pending_user = content
        elif role == "assistant":
            if pending_user is None:
                messages.append(["", content])
            else:
                messages.append([pending_user, content])
                pending_user = None
    return messages


def stream_text(history, assistant_text):
    progressive = ""
    for token in assistant_text.split():
        progressive = f"{progressive} {token}".strip()
        history[-1] = {"role": "assistant", "content": progressive}
        yield history


def assistant_chat(message, history):
    history = history or list(INITIAL_ASSISTANT_MESSAGES)
    if not message or not message.strip():
        yield history_to_chatbot_messages(history), "", history
        return

    prompt = message.strip()
    try:
        result = run_agent(prompt)
        answer = str(result.get("answer", "")).strip() or "I couldn't generate a response."
        sources = result.get("sources") or []
    except Exception as exc:
        answer = f"I hit an error while processing that request: {exc}"
        sources = []

    # Replace last assistant message
    history[-1] = {"role": "assistant", "content": answer + ("\n\nSources:\n" + format_sources(sources) if sources else "")}

    yield history, "", history

    # assistant_message = build_assistant_message(answer, sources)
    # history = history + [
    #     {"role": "user", "content": prompt},
    #     {"role": "assistant", "content": ""},
    # ]

    # for updated_history in stream_text(history, assistant_message):
    #     yield history_to_chatbot_messages(updated_history), "", updated_history


def build_journal_context(results):
    blocks = []
    sources = []
    for index, result in enumerate(results, start=1):
        entry = result["entry"]
        entry_id = entry["id"]
        sources.append(f"{entry['entry_date']} | {entry_id}")
        blocks.append(
            "\n".join(
                [
                    f"[Journal Entry {index}]",
                    f"Date: {entry['entry_date']}",
                    f"Title: {entry.get('title') or 'Untitled'}",
                    f"Mood: {entry.get('mood') or 'n/a'}",
                    f"Tags: {', '.join(entry.get('tags', [])) or 'none'}",
                    f"Content: {entry['content']}",
                ]
            )
        )
    return "\n\n".join(blocks), sources


def journal_chat(user_id, message, history):
    history = history or list(INITIAL_JOURNAL_MESSAGES)
    if not user_id or not user_id.strip():
        invalid_history = history + [{"role": "assistant", "content": "Enter a user ID to chat with the journal."}]
        yield history_to_chatbot_messages(invalid_history), "", history
        return
    if not message or not message.strip():
        yield history_to_chatbot_messages(history), "", history
        return

    store = get_safe_journal_store()
    if store is None:
        response = "Journal database is unavailable. Check `JOURNAL_DATABASE_URL`."
        history = history + [
            {"role": "user", "content": message.strip()},
            {"role": "assistant", "content": response},
        ]
        yield history_to_chatbot_messages(history), "", history
        return

    prompt = message.strip()
    results = store.search_entries(user_id=user_id.strip(), query=prompt, k=5)
    if not results:
        response = "I couldn't find relevant journal entries for that question."
        history = history + [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response},
        ]
        yield history_to_chatbot_messages(history), "", history
        return

    context, sources = build_journal_context(results)
    answer = answer_with_llm(prompt, context, tool="rag")
    assistant_message = build_assistant_message(answer, sources)

    history[-1] = {"role": "assistant", "content": assistant_message}

    yield history, "", history
    # history = history + [
    #     {"role": "user", "content": prompt},
    #     {"role": "assistant", "content": ""},
    # ]

    # for updated_history in stream_text(history, assistant_message):
    #     yield history_to_chatbot_messages(updated_history), "", updated_history


def clear_assistant_chat():
    return history_to_chatbot_messages(INITIAL_ASSISTANT_MESSAGES), "", INITIAL_ASSISTANT_MESSAGES


def clear_journal_chat():
    return history_to_chatbot_messages(INITIAL_JOURNAL_MESSAGES), "", INITIAL_JOURNAL_MESSAGES


def upload_document(file_obj):
    if file_obj is None:
        return "Choose a `.txt`, `.pdf`, or `.xlsx` file to ingest."

    source_path = Path(file_obj)
    if source_path.suffix.lower() not in SUPPORTED_UPLOAD_EXTENSIONS:
        return "Unsupported file type. Use `.txt`, `.pdf`, or `.xlsx`."

    DATA_FOLDER.mkdir(parents=True, exist_ok=True)
    destination = DATA_FOLDER / source_path.name
    shutil.copy(source_path, destination)
    ingest_documents(str(destination))
    return f"Ingested `{destination.name}` into the knowledge base."


def create_journal_entry(user_id, title, content, mood, tags, entry_date):
    if not user_id.strip():
        return "User ID is required."
    if not content.strip():
        return "Journal content is required."

    store = get_safe_journal_store()
    if store is None:
        return "Journal database is unavailable. Check `JOURNAL_DATABASE_URL`."

    payload = JournalEntryCreate(
        user_id=user_id.strip(),
        title=title.strip() or None,
        content=content.strip(),
        mood=mood.strip() or None,
        tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
        entry_date=entry_date or None,
    )
    entry = store.add_entry(payload)
    return f"Saved journal entry `{entry['id']}`."


def update_journal_entry(entry_id, user_id, title, content, mood, tags, entry_date):
    if not entry_id.strip():
        return "Entry ID is required for updates."
    if not user_id.strip():
        return "User ID is required."

    store = get_safe_journal_store()
    if store is None:
        return "Journal database is unavailable. Check `JOURNAL_DATABASE_URL`."

    payload = JournalEntryUpdate(
        title=title.strip() or None,
        content=content.strip() or None,
        mood=mood.strip() or None,
        tags=[tag.strip() for tag in tags.split(",") if tag.strip()] if tags.strip() else None,
        entry_date=entry_date or None,
    )
    entry = store.update_entry(
        entry_id=entry_id.strip(),
        user_id=user_id.strip(),
        payload=payload,
    )
    if entry is None:
        return "Journal entry not found for that user."

    return (
        f"Updated journal entry `{entry['id']}`.\n\n"
        f"created_at: {entry['created_at']}\n"
        f"updated_at: {entry['updated_at']}"
    )


def list_journal_entries(user_id, limit, offset):
    if not user_id.strip():
        return "Enter a user ID to browse journal entries."

    store = get_safe_journal_store()
    if store is None:
        return "Journal database is unavailable. Check `JOURNAL_DATABASE_URL`."

    page = store.list_entries(user_id=user_id.strip(), limit=limit, offset=offset)
    if not page["items"]:
        return "No journal entries found."

    blocks = []
    for item in page["items"]:
        title = item.get("title") or "Untitled"
        mood = item.get("mood") or "n/a"
        tags = ", ".join(item.get("tags", [])) or "none"
        updated = item.get("updated_at") or "never"
        blocks.append(
            "\n".join(
                [
                    f"ID: {item['id']}",
                    f"Title: {title}",
                    f"Date: {item['entry_date']}",
                    f"Mood: {mood}",
                    f"Tags: {tags}",
                    f"Created: {item['created_at']}",
                    f"Updated: {updated}",
                    f"Content: {item['content']}",
                ]
            )
        )

    meta = f"Showing {len(page['items'])} of {page['total']} entries. has_more={page['has_more']}"
    return f"{meta}\n\n" + "\n\n---\n\n".join(blocks)


def search_journal_entries(user_id, query, k):
    if not user_id.strip():
        return "Enter a user ID to search the journal."
    if not query.strip():
        return "Enter a search query."

    store = get_safe_journal_store()
    if store is None:
        return "Journal database is unavailable. Check `JOURNAL_DATABASE_URL`."

    results = store.search_entries(user_id=user_id.strip(), query=query.strip(), k=k)
    if not results:
        return "No matching journal entries found."

    blocks = []
    for result in results:
        entry = result["entry"]
        blocks.append(
            "\n".join(
                [
                    f"Score: {result['score']:.4f}",
                    f"Title: {entry.get('title') or 'Untitled'}",
                    f"Date: {entry['entry_date']}",
                    f"Content: {entry['content']}",
                ]
            )
        )

    return "\n\n---\n\n".join(blocks)


CUSTOM_CSS = """
:root {
  --app-bg: #f7f7f8;
  --panel-bg: #ffffff;
  --border: #e5e7eb;
  --text: #111827;
  --muted: #6b7280;
  --accent: #0f172a;
}
body, .gradio-container {
  background: radial-gradient(circle at top, #ffffff 0%, #f7f7f8 45%, #eef2f7 100%);
  color: var(--text);
}
.gradio-container {
  max-width: 1500px !important;
  margin: 0 auto;
}
#app-shell {
  min-height: 100vh;
}
#hero {
  padding: 16px 0 10px 0;
}
#hero h1 {
  font-size: 2rem;
  line-height: 1.1;
  margin: 0 0 6px 0;
  font-weight: 700;
}
#hero p {
  margin: 0;
  color: var(--muted);
  font-size: 0.98rem;
}
.chat-card, .side-card {
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(18px);
  border: 1px solid rgba(229, 231, 235, 0.95);
  border-radius: 24px;
  box-shadow: 0 18px 60px rgba(15, 23, 42, 0.06);
}
.chat-card {
  padding: 10px;
}
.side-card {
  padding: 14px;
}
.section-title {
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 10px;
}
.soft-note {
  font-size: 0.92rem;
  color: var(--muted);
}
.compact-button button {
  border-radius: 14px !important;
}
"""


with gr.Blocks(title=APP_TITLE, fill_height=True, fill_width=True) as demo:
    assistant_state = gr.State(INITIAL_ASSISTANT_MESSAGES)
    journal_state = gr.State(INITIAL_JOURNAL_MESSAGES)

    gr.HTML(
        f"""
        <div id="app-shell">
          <div id="hero">
            <h1>{APP_TITLE}</h1>
            <p>{APP_SUBTITLE}</p>
          </div>
        </div>
        """
    )

    with gr.Row(equal_height=True):
        with gr.Column(scale=7):
            with gr.Tabs():
                with gr.Tab("Assistant"):
                    with gr.Group(elem_classes=["chat-card"]):
                        assistant_chatbot = gr.Chatbot(
                            value=INITIAL_ASSISTANT_MESSAGES,
                            height=640,
                            layout="bubble",
                            avatar_images=(None, None),
                            label="Knowledge Copilot",
                            placeholder="Start a conversation with your knowledge assistant.",
                            **CHATBOT_KWARGS,
                        )
                        with gr.Row():
                            assistant_msg = gr.Textbox(
                                placeholder="Message AI RAG Agent...",
                                lines=1,
                                scale=8,
                                show_label=False,
                            )
                            assistant_send = gr.Button("Send", variant="primary", scale=1, elem_classes=["compact-button"])
                        assistant_clear = gr.Button("New chat")

                with gr.Tab("Journal Copilot"):
                    with gr.Group(elem_classes=["chat-card"]):
                        journal_chat_user_id = gr.Textbox(
                            label="Journal User ID",
                            value="demo-user",
                            info="Used to scope journal search and reflection.",
                        )
                        journal_chatbot = gr.Chatbot(
                            value=INITIAL_JOURNAL_MESSAGES,
                            height=580,
                            layout="bubble",
                            avatar_images=(None, None),
                            label="Journal Reflection Chat",
                            placeholder="Ask reflective questions about your journal.",
                            **CHATBOT_KWARGS,
                        )
                        with gr.Row():
                            journal_msg = gr.Textbox(
                                placeholder="Ask your journal something...",
                                lines=1,
                                scale=8,
                                show_label=False,
                            )
                            journal_send = gr.Button("Send", variant="primary", scale=1, elem_classes=["compact-button"])
                        journal_clear = gr.Button("New journal chat")

        with gr.Column(scale=4):
            with gr.Group(elem_classes=["side-card"]):
                gr.HTML('<div class="section-title">Knowledge Base</div>')
                gr.Markdown("Upload a file to extend retrieval context for the assistant.")
                upload = gr.File(
                    label="Document",
                    file_types=[".txt", ".pdf", ".xlsx"],
                    type="filepath",
                )
                upload_btn = gr.Button("Ingest document", variant="secondary", elem_classes=["compact-button"])
                upload_status = gr.Markdown("No document uploaded yet.", elem_classes=["soft-note"])

            with gr.Group(elem_classes=["side-card"]):
                gr.HTML('<div class="section-title">Quick Journal Entry</div>')
                journal_entry_id = gr.Textbox(
                    label="Entry ID (for update only)",
                    placeholder="Paste an existing journal entry id to update it",
                )
                journal_user_id = gr.Textbox(label="User ID", value="demo-user")
                journal_title = gr.Textbox(label="Title")
                journal_content = gr.Textbox(label="Entry", lines=5)
                journal_mood = gr.Textbox(label="Mood")
                journal_tags = gr.Textbox(label="Tags", placeholder="comma,separated,tags")
                journal_date = gr.Textbox(label="Entry Date", placeholder="YYYY-MM-DD (optional)")
                with gr.Row():
                    journal_save = gr.Button("Create entry", variant="secondary", elem_classes=["compact-button"])
                    journal_update = gr.Button("Update entry", variant="primary", elem_classes=["compact-button"])
                journal_save_status = gr.Markdown(elem_classes=["soft-note"])

            with gr.Accordion("Browse Journal", open=False):
                journal_limit = gr.Slider(1, 50, value=10, step=1, label="Limit")
                journal_offset = gr.Slider(0, 200, value=0, step=1, label="Offset")
                journal_list_btn = gr.Button("Load entries")
                journal_list_output = gr.Textbox(label="Entries", lines=12)

            with gr.Accordion("Search Journal", open=False):
                journal_query = gr.Textbox(label="Search query")
                journal_k = gr.Slider(1, 10, value=5, step=1, label="Top K")
                journal_search_btn = gr.Button("Search journal")
                journal_search_output = gr.Textbox(label="Search results", lines=10)

    assistant_send.click(
        fn=assistant_chat,
        inputs=[assistant_msg, assistant_state],
        outputs=[assistant_chatbot, assistant_msg, assistant_state],
    )
    assistant_msg.submit(
        fn=assistant_chat,
        inputs=[assistant_msg, assistant_state],
        outputs=[assistant_chatbot, assistant_msg, assistant_state],
    )
    assistant_clear.click(
        fn=clear_assistant_chat,
        outputs=[assistant_chatbot, assistant_msg, assistant_state],
    )

    journal_send.click(
        fn=journal_chat,
        inputs=[journal_chat_user_id, journal_msg, journal_state],
        outputs=[journal_chatbot, journal_msg, journal_state],
    )
    journal_msg.submit(
        fn=journal_chat,
        inputs=[journal_chat_user_id, journal_msg, journal_state],
        outputs=[journal_chatbot, journal_msg, journal_state],
    )
    journal_clear.click(
        fn=clear_journal_chat,
        outputs=[journal_chatbot, journal_msg, journal_state],
    )

    upload_btn.click(fn=upload_document, inputs=upload, outputs=upload_status)
    journal_save.click(
        fn=create_journal_entry,
        inputs=[journal_user_id, journal_title, journal_content, journal_mood, journal_tags, journal_date],
        outputs=journal_save_status,
    )
    journal_update.click(
        fn=update_journal_entry,
        inputs=[
            journal_entry_id,
            journal_user_id,
            journal_title,
            journal_content,
            journal_mood,
            journal_tags,
            journal_date,
        ],
        outputs=journal_save_status,
    )
    journal_list_btn.click(
        fn=list_journal_entries,
        inputs=[journal_user_id, journal_limit, journal_offset],
        outputs=journal_list_output,
    )
    journal_search_btn.click(
        fn=search_journal_entries,
        inputs=[journal_user_id, journal_query, journal_k],
        outputs=journal_search_output,
    )


if __name__ == "__main__":
    demo.launch()
