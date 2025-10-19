from typing import List, Dict
import numpy as np
import faiss

def retrieve(
    index: faiss.IndexFlatL2,
    records: List[Dict],
    query_embedding: np.ndarray,
    top_k: int = 5
) -> List[Dict]:
    """
    Search FAISS and return top_k records with scores.
    Each result: {"text": str, "metadata": dict, "score": float}
    """
    if index.ntotal == 0:
        return []
    q = np.array([query_embedding], dtype="float32")
    D, I = index.search(q, k=min(top_k, max(1, index.ntotal)))
    out: List[Dict] = []
    for pos, idx in enumerate(I[0]):
        if 0 <= idx < len(records):
            out.append({
                "text": records[idx]["text"],
                "metadata": records[idx]["metadata"],
                "score": float(D[0][pos]),
            })
    return out
