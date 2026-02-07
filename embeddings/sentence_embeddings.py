from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_texts(texts: list[str]):
    return _model.encode(texts, normalize_embeddings=True)

def embed_query(query: str):
    return _model.encode([query], normalize_embeddings=True)[0]
