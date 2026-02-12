from sentence_transformers import SentenceTransformer

_model = SentenceTransformer(
    "all-MiniLM-L6-v2",
    local_files_only=True
)

def embed_texts(texts):
    return _model.encode(texts, normalize_embeddings=True)

def embed_query(query):
    return _model.encode([query], normalize_embeddings=True)[0]
