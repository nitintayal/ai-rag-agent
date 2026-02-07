from dotenv import load_dotenv

from ingestion.load_documents import load_text_documents
from ingestion.chunk_documents import chunk_text
from embeddings.sentence_embeddings import embed_texts, embed_query
from retrieval.vector_store import VectorStore
from pathlib import Path
from agent.local_llm_answer import answer_with_llm


def main():
    load_dotenv()

    print("📄 Loading documents...")
    documents = load_text_documents("data")

    # ---- Chunk documents ----
    print("✂️ Chunking documents...")
    chunks = []
    for doc in documents:
        for chunk in chunk_text(doc["content"]):
            chunks.append({
                "source": doc["source"],
                "content": chunk
            })

    texts = [c["content"] for c in chunks]

    print(f"✅ Loaded {len(documents)} documents")
    print(f"✂️ Created {len(texts)} chunks")

    STORE_PATH = "storage"

    # ---- Build or load vector store ----
    if Path(f"{STORE_PATH}/faiss.index").exists():
        print("📦 Loading vector store from disk...")
        store = VectorStore.load(STORE_PATH)
    else:
        print("🧠 Creating embeddings...")
        vectors = embed_texts(texts)

        print("📦 Building vector store...")
        store = VectorStore.from_vectors(vectors, chunks)

        print("💾 Saving vector store...")
        store.save(STORE_PATH)

    # # 🔍 Inspect a sample embedding
    # print("\n🔢 Sample embedding inspection:")
    # print("Vector length:", len(vectors[0]))
    # print("First 10 values:", vectors[0][:10])

    # # ---- Build vector store ----
    # print("📦 Building FAISS vector store...")
    # store = VectorStore(vectors, chunks)

    # ---- Ask a question ----
    question = "Password expiry time?"
    print(f"\n❓ Question: {question}")

    query_vector = embed_query(question)

    # ---- Semantic search ----
    results = store.search(query_vector, k=3)

    # ---- Collect citations ----
    sources = sorted(set(r["document"]["source"] for r in results))

    # ---- Confidence score ----
    avg_confidence = sum(r["score"] for r in results) / len(results)
    confidence_percent = round(avg_confidence * 100, 2)
    print(f"\n💡 Confidence Score: {confidence_percent}%")


    print("\n🔍 Top search results:\n")
    for i, r in enumerate(results, start=1):
        print(f"{i}. Source: {r['document']['source']}")
        print(r['document']['content'])
        print("-" * 40)
        # ---- Build context for LLM ----
        context = "\n\n".join(
            f"[Source: {r['document']['source']}]\n{r['document']['content']}"
            for r in results
        )

    print("\n🤖 Generating answer with Model...\n")
    answer = answer_with_llm(question, context)

    print("📝 Final Answer:\n")
    print(answer)

    print(f"\n📊 Confidence: {confidence_percent}%")

    print("\n📚 Sources:")
    for s in sources:
        print(f"- {s}")



if __name__ == "__main__":
    main()
