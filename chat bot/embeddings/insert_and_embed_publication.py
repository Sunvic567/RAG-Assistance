import uuid
import torch
from typing import List
from embeddings.chunk_publication import chunking_publication
from langchain_community.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv

# new import: Supabase memory helper
from memory.memory import ensure_table, insert_memory

load_dotenv()

# device-aware, reusable embedding instance
device = (
    "cuda" if torch.cuda.is_available()
    else "mps" if torch.backends.mps.is_available() else "cpu"
)
embedding = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": device},
)

# ensure DB table exists
try:
    ensure_table()
except Exception as e:
    print(f"Warning: could not ensure memories table: {e}")

def embed_documents(document: List[str]) -> List[List[float]]:
    return embedding.embed_documents(document)


def insert_publication(publications: List[str]) -> None:
    total_inserted = 0
    for publication in publications:
        title = f"doc_{uuid.uuid4().hex[:8]}"
        chunked_publication = chunking_publication(publication, title)
        texts = [chunk["content"] for chunk in chunked_publication]
        if not texts:
            continue

        # embed in batches (reuse embed_documents)
        try:
            embeddings = embed_documents(texts)
        except Exception as e:
            print(f"Embedding error for {title}: {e}")
            continue

        if len(embeddings) != len(texts):
            print(f"Embedding count mismatch for {title}; skipping.")
            continue

        for chunk, emb in zip(chunked_publication, embeddings):
            metadata = {"title": chunk["title"], "chunk_id": chunk["chunk_id"]}
            try:
                insert_memory(chunk["content"], emb, metadata)
                total_inserted += 1
            except Exception as e:
                print(f"Insert memory error for chunk {metadata}: {e}")

    print(f"Inserted {total_inserted} chunks into Supabase memories.")
    return











