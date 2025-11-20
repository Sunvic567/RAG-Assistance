import os
import uuid
import torch
from typing import List, Dict
from dotenv import load_dotenv
from config.settings import PINECONE_API_KEY
from config.settings import PINECONE_ENV
from config.settings import PINECONE_INDEX

from embeddings.chunk_publication import chunking_publication
from langchain_huggingface import HuggingFaceEmbeddings

# Pinecone
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

# Pinecone config from env
PINECONE_API_KEY = PINECONE_API_KEY
PINECONE_ENV =  PINECONE_ENV
PINECONE_INDEX =  PINECONE_INDEX

if not PINECONE_API_KEY:
    raise RuntimeError("PINECONE_API_KEY environment variable is required for Pinecone integration.")

# DEVICE + EMBEDDINGS
device = (
    "cuda" if torch.cuda.is_available()
    else "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
    else "cpu"
)

embedding = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": device},
)

# initialize pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# ensure index exists (dimension must match the embedding model; all-MiniLM-L6-v2 -> 384)
EMBED_DIM = 384
indexes = [idx["name"] for idx in pc.list_indexes()]
if PINECONE_INDEX not in pc.list_indexes().names():
    pc.create_index(name=PINECONE_INDEX, 
                         dimension=EMBED_DIM,
                         metric="cosine",
                         spec=ServerlessSpec(
                         cloud='aws',
                         region='us-east-1'
                         ),
                        )

index = pc.Index(name=PINECONE_INDEX)



# HELPERS

def embed_documents(documents: List[str]) -> List[List[float]]:
    return embedding.embed_documents(documents)


def upsert_batch(vectors: List[Dict], batch_size: int = 100):
    """
    vectors: list of dicts with keys: id(str), values(list[float]), metadata(dict)
    """
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        to_upsert = [(v["id"], v["values"], v.get("metadata")) for v in batch]
        try:
            index.upsert(vectors=to_upsert)
        except Exception as e:
            print(f"[PINECONE UPSERT ERROR] batch starting at {i}: {e}")


# MAIN INGESTION PIPELINE

def insert_publication(publications: List[str]) -> int:
    """
    Chunk publications, embed chunks, and insert into Pinecone.
    Returns number of chunks inserted.
    """
    total_inserted = 0
    for publication in publications:
        title = f"doc_{uuid.uuid4().hex[:8]}"
        chunks = chunking_publication(publication, title)

        texts = [c["content"] for c in chunks]
        if not texts:
            continue

        # embeddings
        try:
            embeddings = embed_documents(texts)
        except Exception as e:
            print(f"[EMBED ERROR] {title}: {e}")
            continue

        if len(embeddings) != len(texts):
            print(f"[ERROR] Embedding mismatch for {title}")
            continue

        vectors = []
        for chunk, emb in zip(chunks, embeddings):
            # ensure embedding is list of floats
            vector = list(map(float, emb))
            chunk_id = chunk.get("chunk_id") or f"{title}_{uuid.uuid4().hex[:8]}"
            metadata = {
                'content': chunk['content'],
                "title": chunk.get("title"),
                "chunk_id": chunk_id,
            }
            vectors.append({"id": chunk_id, "values": vector, "metadata": metadata})
            total_inserted += 1

        # upsert into pinecone in batches
        upsert_batch(vectors, batch_size=100)

    print(f"Inserted {total_inserted} chunks into Pinecone index '{PINECONE_INDEX}'.")
    return total_inserted