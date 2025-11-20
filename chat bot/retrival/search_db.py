from typing import List, Optional
from embeddings.insert_and_embed_publication import embedding
from embeddings.insert_and_embed_publication import index


def search_research_db(
    query: str,
    
    embedding_instance=None,
    top_k: int = 3,
    session_id: Optional[str] = None
) -> List[dict]:
    if embedding_instance is None:
        embedding_instance = embedding

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
        response = index.query(
            vector=qvec,
            top_k=top_k,
            include_metadata=True,
            namespace=session_id
        )
    except Exception as e:
        print(f"Pinecone vector search error: {e}")
        return []
    results = []
    for m in response.matches:
            results.append({
                "content": m.metadata.get("content"),
                "title": m.metadata.get("title"),
                "chunk_id": m.id,
                "score": m.score
            })
    return results