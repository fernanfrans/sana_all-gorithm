from sentence_transformers import SentenceTransformer

LOCAL_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

def embed_chunks(chunks):
    texts = [chunk["text"] for chunk in chunks]
    local_embeddings = LOCAL_MODEL.encode(texts).tolist()

    return [
        {
            "embedding": emb,
            "text": chunks[i]["text"],
            "metadata": chunks[i].get("metadata", {})
        }
        for i, emb in enumerate(local_embeddings)
    ]


def embed_query(query: str):
    """Embed a single query string."""
    return LOCAL_MODEL.encode([query])[0].tolist()
