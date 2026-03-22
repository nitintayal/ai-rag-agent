import tiktoken

def chunk_documents(documents, chunk_size=400, overlap=80):

    enc = tiktoken.get_encoding("cl100k_base")

    chunks = []

    for doc in documents:

        text = doc["content"]
        tokens = enc.encode(text)

        start = 0

        while start < len(tokens):

            end = start + chunk_size

            chunk_tokens = tokens[start:end]

            chunk_text = enc.decode(chunk_tokens)

            chunks.append({
                "content": chunk_text,
                "source": doc["source"]
            })

            start += chunk_size - overlap

    return chunks
