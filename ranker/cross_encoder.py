from sentence_transformers import CrossEncoder

# lightweight & fast
model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank(query, docs):

    pairs = [(query, d["content"]) for d in docs]

    scores = model.predict(pairs)

    # 👇 ADD DEBUG HERE
    print("\n🔍 Cross-Encoder Scores:")
    for doc, score in zip(docs, scores):
        print(f"{score:.4f} → {doc['content'][:80]}")

    ranked = sorted(
        zip(docs, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return [r[0] for r in ranked]
