from agent.agent_executor import run_agent


DEMO_QUESTIONS = [
    "Summarize the uploaded knowledge base.",
    "What are the most important employee policy facts?",
    "What security guidance exists in the documents?",
    "What is the latest news about AI agents?",
]


def main():
    for index, question in enumerate(DEMO_QUESTIONS, start=1):
        print(f"\n[{index}] {question}")
        try:
            result = run_agent(question)
        except Exception as exc:
            print(f"ERROR: {exc}")
            continue

        answer = str(result.get("answer", "")).strip()
        tool = result.get("tool", "unknown")
        sources = result.get("sources") or []

        print(f"Route: {tool}")
        print(f"Answer: {answer[:500] or 'No answer returned.'}")
        print(f"Sources: {sources[:5]}")


if __name__ == "__main__":
    main()
