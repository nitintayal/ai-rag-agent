from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer("all-MiniLM-L6-v2")

sentences = [
    "Passwords must be changed every 90 days",
    "How often should passwords be updated?",
    "The office opens at 9 AM"
]

embeddings = model.encode(sentences)

similarity = cosine_similarity(
    [embeddings[0]],
    [embeddings[1]]
)

print(similarity)
