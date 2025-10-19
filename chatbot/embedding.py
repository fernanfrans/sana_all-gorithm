from typing import Dict, Generator, List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# Load once
LOCAL_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

def _embed_texts_batch(texts: List[str]) -> np.ndarray:
    # Sentence-Transformers returns np.ndarray; we ensure float32 for FAISS
    arr = LOCAL_MODEL.encode(texts, convert_to_numpy=True, normalize_embeddings=False)
    return arr.astype("float32")

def embed_query(query: str) -> np.ndarray:
    vec = LOCAL_MODEL.encode([query], convert_to_numpy=True)[0]
    return vec.astype("float32")

def build_faiss_index_from_chunks(
    chunks_iter: Generator[Dict, None, None],
    batch_size: int = 512
) -> Tuple[faiss.IndexFlatL2, List[Dict], int]:
    """
    Stream chunks, embed in batches, and build a FAISS index incrementally.
    Returns: (faiss_index, records_list, dim)
      - records_list[i] corresponds to vector at position i in the FAISS index
        and has keys: {"text": str, "metadata": dict}
    """
    records: List[Dict] = []
    batch_texts: List[str] = []
    batch_records: List[Dict] = []
    index = None
    dim = None

    def _flush_batch():
        nonlocal index, dim, records, batch_texts, batch_records
        if not batch_texts:
            return
        embs = _embed_texts_batch(batch_texts)  # shape (B, D)
        if index is None:
            dim = int(embs.shape[1])
            index = faiss.IndexFlatL2(dim)
        index.add(embs)
        records.extend(batch_records)
        batch_texts, batch_records = [], []

    for chunk in chunks_iter:
        batch_texts.append(chunk["text"])
        batch_records.append({"text": chunk["text"], "metadata": chunk.get("metadata", {})})
        if len(batch_texts) >= batch_size:
            _flush_batch()

    _flush_batch()  # final

    if index is None:
        # No data; create empty index of reasonable dim (use model dim)
        dim = int(LOCAL_MODEL.get_sentence_embedding_dimension())
        index = faiss.IndexFlatL2(dim)
    return index, records, dim
