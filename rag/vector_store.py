import faiss
import numpy as np
import pickle
from pathlib import Path
from rank_bm25 import BM25Okapi
import re
from configs.config import settings

class VectorStore:
    def __init__(self, index=None, documents=None):
        self.index = index
        self.documents = documents or []

    def add(self, vectors, documents):
        if self.index is None:
            self.index = faiss.IndexFlatIP(len(vectors[0]))
        self.index.add(np.array(vectors).astype("float32"))
        self.documents.extend(documents)

    def tokenize(self, text):
        return re.findall(r"\w+", text.lower())

    @classmethod
    def from_vectors(cls, vectors, documents):
        dim = len(vectors[0])
        index = faiss.IndexFlatIP(dim)
        index.add(np.array(vectors).astype("float32"))
        return cls(index, documents)

    def search(self, query_vector, k=3):
        
        distances, indices = self.index.search(
            np.array([query_vector]).astype("float32"), k
        )

        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.documents):
                continue
            results.append({
                "document": self.documents[idx],
                "score": float(score)
            })

        return results


    def save(self, folder_path="storage"):
        Path(folder_path).mkdir(exist_ok=True)

        faiss.write_index(self.index, f"{folder_path}/faiss.index")

        with open(f"{folder_path}/documents.pkl", "wb") as f:
            pickle.dump(self.documents, f)

    @classmethod
    def load(cls, folder_path="storage"):
        index = faiss.read_index(f"{folder_path}/faiss.index")

        with open(f"{folder_path}/documents.pkl", "rb") as f:
            documents = pickle.load(f)

        store = cls(index, documents)
        store.build_bm25()

        return store

    def delete_by_source(self, source):

        import numpy as np
        import faiss

        new_documents = []
        new_vectors = []

        for i, doc in enumerate(self.documents):

            if doc["source"] != source:

                new_documents.append(doc)

                vector = self.index.reconstruct(i)

                new_vectors.append(vector)

        if not new_vectors:
            print("No vectors left")

            dim = self.index.d
            self.index = faiss.IndexFlatIP(dim)

            self.documents = []

            return

        vectors_np = np.array(new_vectors).astype("float32")

        dim = vectors_np.shape[1]

        new_index = faiss.IndexFlatIP(dim)

        new_index.add(vectors_np)

        self.index = new_index
        self.documents = new_documents

    def build_bm25(self):

        self.corpus = [doc["content"] for doc in self.documents]
        tokenized_corpus = [self.tokenize(text) for text in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def hybrid_search(self, query, query_vector, k=5):

        import numpy as np

        # 1️⃣ Vector search
        D, I = self.index.search(np.array([query_vector]).astype("float32"), k)

        vector_results = []
        for idx, score in zip(I[0], D[0]):
            if idx < 0 or idx >= len(self.documents):
                continue
            vector_results.append({
                "doc": self.documents[idx],
                "score": float(score)
            })

        # 2️⃣ BM25 search
        tokenized_query = self.tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)

        bm25_results = []
        for i, score in enumerate(bm25_scores):
            bm25_results.append({
                "doc": self.documents[i],
                "score": score
            })

        # 3️⃣ Normalize scores
        def normalize(scores):
            if not scores:
                return []
            min_score = min(scores)
            max_score = max(scores)
            if max_score == min_score:
                return [1.0 for _ in scores]
            return [(s - min_score) / (max_score - min_score) for s in scores]

        vec_scores = normalize([r["score"] for r in vector_results])
        bm_scores = normalize([r["score"] for r in bm25_results])

        # 4️⃣ Combine scores
        combined = {}

        for i, r in enumerate(vector_results):
            key = r["doc"]["chunk_id"]
            combined[key] = settings.VECTOR_WEIGHT * vec_scores[i]

        for i, r in enumerate(bm25_results):
            key = r["doc"]["chunk_id"]
            combined[key] = combined.get(key, 0) + settings.BM25_WEIGHT * bm_scores[i]

        # 5️⃣ Sort results
        sorted_docs = sorted(combined.items(), key=lambda x: x[1], reverse=True)

        # 6️⃣ Return top-k documents
        results = []
        for content, score in sorted_docs[:k]:
            doc = next(d for d in self.documents if d["chunk_id"] == content)
            results.append({
                "document": doc,
                "score": score
            })

        return results
