from dotenv import load_dotenv
from ingestion.load_documents import load_text_documents

def main():
    load_dotenv()

    docs = load_text_documents("data")

    print(f"📄 Loaded {len(docs)} document(s)\n")

    for doc in docs:
        print(f"--- {doc['source']} ---")
        print(doc["content"])
        print()

if __name__ == "__main__":
    main()
