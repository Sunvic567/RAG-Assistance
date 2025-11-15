from typing import List, Optional
from memory.memory import search_memories
from embeddings.insert_and_embed_publication import embedding as default_embedding

def search_research_db(
    query: str,
    _collection=None,
    embedding_instance=None,
    top_k: int = 3,
    session_id: Optional[str] = None
) -> List[dict]:
    if embedding_instance is None:
        embedding_instance = default_embedding

    try:
        # prefer embed_query, fall back to embed_documents for single-item embedding
        if hasattr(embedding_instance, "embed_query"):
            qvec = embedding_instance.embed_query(query)
        else:
            qvec = embedding_instance.embed_documents([query])[0]
    except Exception as e:
        print(f"Query embedding error: {e}")
        return []

    try:
        # attempt to pass session_id if supported by search_memories
        try:
            if session_id is not None:
                rows = search_memories(qvec, top_k=top_k, session_id=session_id)
            else:
                rows = search_memories(qvec, top_k=top_k)
        except TypeError:
            # fallback if search_memories doesn't accept session_id kwarg
            rows = search_memories(qvec, top_k=top_k)
    except Exception as e:
        print(f"Search memories error: {e}")
        return []

    if not rows:
        return []

    results = []
    for r in rows:
        meta = r.get("metadata") or {}
        results.append({
            "content": r.get("content"),
            "title": meta.get("title"),
            "chunk_id": meta.get("chunk_id"),
            "similarity": r.get("similarity"),
        })
    return results
