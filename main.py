from dotenv import load_dotenv

from ingestion.load_documents import load_documents
from ingestion.chunk_documents import chunk_documents
from embeddings.sentence_embeddings import embed_texts, embed_query
from retrieval.vector_store import VectorStore
from pathlib import Path
from agent.local_llm_answer import answer_with_llm
from configs.config import settings
DATA_FOLDER = Path(settings.DATA_DIR)
STORAGE_FOLDER = Path(settings.STORAGE_DIR)

def main():
    load_dotenv()

    print("📄 Loading documents...")
    documents = load_documents(DATA_FOLDER)

    # ---- Chunk documents ----
    print("✂️ Chunking documents...")
    
    chunks = chunk_documents(documents)

    texts = [c["content"] for c in chunks]

    print(f"✅ Loaded {len(documents)} documents")
    print(f"✂️ Created {len(texts)} chunks")

    # ---- Build or load vector store ----
    if Path(f"{STORAGE_FOLDER}/faiss.index").exists():
        print("📦 Loading vector store from disk...")
        store = VectorStore.load(STORAGE_FOLDER)
        existing_sources = set(doc["source"] for doc in store.documents)
        print(f"✅ Loaded vector store with {len(existing_sources)} old documents")
        new_docs = [
            doc for doc in documents
            if doc["source"] not in existing_sources
        ]
        print(f"🔍 Found {len(new_docs)} new documents to add")
        if new_docs:
            print(f"➕ Found {len(new_docs)} new documents. Updating vector store...")
            new_chunks = []
            for doc in new_docs:
                for chunk in chunk_text(doc["content"]):
                    new_chunks.append({
                        "source": str(doc["source"]),
                        "content": chunk
                    })
            new_texts = [c["content"] for c in new_chunks]
            new_vectors = embed_texts(new_texts)
            store.add(new_vectors, new_chunks)
            store.save(STORAGE_FOLDER)
    else:
        print("🧠 Creating embeddings...")
        vectors = embed_texts(texts)

        print("📦 Building vector store...")
        store = VectorStore.from_vectors(vectors, chunks)

        print("💾 Saving vector store...")
        store.save(STORAGE_FOLDER)

    # # 🔍 Inspect a sample embedding
    # print("\n🔢 Sample embedding inspection:")
    # print("Vector length:", len(vectors[0]))
    # print("First 10 values:", vectors[0][:10])

    # # ---- Build vector store ----
    # print("📦 Building FAISS vector store...")
    # store = VectorStore(vectors, chunks)

    # ---- Ask a question ----
    while True:
        question = input("\n❓ Ask your question (type 'exit' to quit): ")

        if question.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break

        query_vector = embed_query(question)
        results = store.search(query_vector, k=5)

        context = "\n\n".join(
            f"[Source: {r['document']['source']}]\n{r['document']['content']}"
            for r in results
        )

        print("\n🤖 Generating answer with Model...\n")
        answer = answer_with_llm(question, context)

        print("📝 Final Answer:\n")
        print(answer)
                # ---- Collect citations ----
        sources = sorted(set(r["document"]["source"] for r in results))

        # ---- Confidence score ----
        avg_confidence = sum(r["score"] for r in results) / len(results)
        confidence_percent = round(avg_confidence * 100, 2)
        print(f"\n💡 Confidence Score: {confidence_percent}%")

        print("\n📚 Sources:")
        for s in sources:
            print(f"- {s}")




    # print("\n🔍 Top search results:\n")
    # for i, r in enumerate(results, start=1):
    #     print(f"{i}. Source: {r['document']['source']}")
    #     print(r['document']['content'])
    #     print("-" * 40)
    #     # ---- Build context for LLM ----
    #     context = "\n\n".join(
    #         f"[Source: {r['document']['source']}]\n{r['document']['content']}"
    #         for r in results
    #     )







if __name__ == "__main__":
    main()
