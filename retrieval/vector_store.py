import faiss
import numpy as np
import pickle
from pathlib import Path


class VectorStore:
    def __init__(self, index=None, documents=None):
        self.index = index
        self.documents = documents or []

    def add(self, vectors, documents):
        self.index.add(np.array(vectors).astype("float32"))
        self.documents.extend(documents)

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

        return cls(index, documents)

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
            self.index = faiss.IndexFlatL2(dim)

            self.documents = []

            return

        vectors_np = np.array(new_vectors).astype("float32")

        dim = vectors_np.shape[1]

        new_index = faiss.IndexFlatL2(dim)

        new_index.add(vectors_np)

        self.index = new_index
        self.documents = new_documents
