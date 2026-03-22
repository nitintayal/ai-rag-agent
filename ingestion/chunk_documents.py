import tiktoken
from configs.config import settings

def chunk_documents(documents, chunk_size=None, overlap=None):

    if chunk_size is None:
        chunk_size = settings.CHUNK_SIZE
    if overlap is None:
        overlap = settings.CHUNK_OVERLAP

    enc = tiktoken.get_encoding("cl100k_base")

    chunks = []

    for doc in documents:

        text = doc["content"]
        tokens = enc.encode(text)

        start = 0
        chunk_idx = 0
        while start < len(tokens):

            end = start + chunk_size

            chunk_tokens = tokens[start:end]

            chunk_text = enc.decode(chunk_tokens)

            chunks.append({
                "content": chunk_text,
                "source": doc["source"],
                "chunk_id": f"{doc['source']}_{chunk_idx}"
            })

            start += chunk_size - overlap
            chunk_idx += 1

    return chunks
