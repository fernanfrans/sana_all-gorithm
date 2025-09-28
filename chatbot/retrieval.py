import faiss
import numpy as np

def build_faiss_index(embeddings):
    """
    Build a FAISS index from a list of embeddings.
    Each embedding dict must have 'embedding'.
    """
    dim = len(embeddings[0]["embedding"])
    index = faiss.IndexFlatL2(dim)

    vectors = np.array([e["embedding"] for e in embeddings]).astype("float32")
    index.add(vectors)

    return index


def retrieve(query, index, embeddings, query_embedding):
    """
    Retrieve top-k relevant chunks given a query embedding.
    """
    query_vector = np.array([query_embedding]).astype("float32")
    D, I = index.search(query_vector, k=5)  # top-5 results

    results = []
    for idx in I[0]:
        if idx < len(embeddings):  # guard against out of range
            results.append(embeddings[idx])
    return results
