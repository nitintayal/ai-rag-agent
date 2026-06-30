from rag.load_documents import load_documents, load_single_file, resolve_data_path
from rag.chunk_documents import chunk_documents
from rag.embeddings import embed_texts
from rag.vector_store import VectorStore
from configs.config import settings


def ingest_documents(single_file=None):
    storage_dir = resolve_data_path(settings.STORAGE_DIR)

    print("📄 Loading documents...")

    doc = load_single_file(single_file) if single_file else load_documents(settings.DATA_DIR)

    if not doc:
        print("⚠️ No documents found to ingest.")
        return {"documents": 0, "chunks": 0, "status": "empty"}

    print(f"Loaded {len(doc)} documents")

    print("✂️ Chunking documents...")
    chunks = chunk_documents(doc)

    texts = [c["content"] for c in chunks]

    print(f"Created {len(chunks)} chunks")


    print("🧠 Generating embeddings...")

    embeddings = embed_texts(texts)

    print("📦 Updating vector store...")

    try:
        store = VectorStore.load(storage_dir)
        store.add(embeddings, chunks)
        store.build_bm25()
        store.save(storage_dir)
    except Exception:
        store = VectorStore.from_vectors(embeddings, chunks)
        store.save(storage_dir)

    print("✅ Ingestion complete")
    return {
        "documents": len(doc),
        "chunks": len(chunks),
        "status": "ok",
        "sources": sorted({str(item["source"]) for item in doc}),
    }
