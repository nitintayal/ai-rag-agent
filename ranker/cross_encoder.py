from sentence_transformers import CrossEncoder
from configs.config import settings
# lightweight & fast
model = CrossEncoder(settings.RERANK_MODEL)

def rerank(query, docs):
    ranked = rerank_with_scores(query, docs)
    return [item["document"] for item in ranked]


def rerank_with_scores(query, docs):
    if not docs:
        return []

    pairs = [(query, d["content"]) for d in docs]

    scores = model.predict(pairs)

    # 👇 ADD DEBUG HERE
    print("\n🔍 Cross-Encoder Scores:")
    for doc, score in zip(docs, scores):
        print(f"{score:.4f} → {doc['content'][:80]}")

    ranked = sorted(
        (
            {
                "document": doc,
                "score": float(score),
            }
            for doc, score in zip(docs, scores)
        ),
        key=lambda x: x["score"],
        reverse=True
    )

    return ranked
