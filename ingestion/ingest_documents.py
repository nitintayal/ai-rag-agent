from ingestion.load_documents import load_documents, load_single_file
from ingestion.chunk_documents import chunk_text
from embeddings.sentence_embeddings import embed_texts
from retrieval.vector_store import VectorStore


def ingest_documents(single_file=None):

    print("📄 Loading documents...")

    doc = load_single_file(single_file) if single_file else load_documents("data")

    print(f"Loaded {len(doc)} documents")

    print("✂️ Chunking documents...")

    chunks = []
    for chunk in chunk_text(doc["content"]):
        chunks.append({
            "source": str(doc["source"]),
            "content": chunk
        })

    texts = [c["content"] for c in chunks]

    print(f"Created {len(chunks)} chunks")


    print("🧠 Generating embeddings...")

    embeddings = embed_texts(texts)

    print("📦 Updating vector store...")

    store = VectorStore.load()

    store.add(embeddings, chunks)

    store.save()

    print("✅ Ingestion complete")