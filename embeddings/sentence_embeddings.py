from sentence_transformers import SentenceTransformer
from configs.config import settings

_model = SentenceTransformer(
    settings.EMBEDDING_MODEL
)

def embed_texts(texts):
    return _model.encode(texts, normalize_embeddings=True)

def embed_query(query):
    return _model.encode([query], normalize_embeddings=True)[0]
