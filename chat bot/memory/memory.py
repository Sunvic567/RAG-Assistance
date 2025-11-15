import os
import json
import logging
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))

if not DB_URL or not DB_URL.startswith(("postgres://", "postgresql://")):
    raise RuntimeError(
        "SUPABASE_DB_URL must be a Postgres DSN (postgres://... or postgresql://...). "
        "Set SUPABASE_DB_URL in your .env with the Postgres connection string from Supabase."
    )

# DB deps
try:
    from psycopg_pool import ConnectionPool
    from pgvector.psycopg import register_vector
    from pgvector import Vector
except Exception as e:
    raise RuntimeError(f"Missing DB dependencies: {e}. Run: pip install 'psycopg[binary]' pgvector psycopg_pool")

POOL_MIN = int(os.getenv("DB_POOL_MIN", "1"))
POOL_MAX = int(os.getenv("DB_POOL_MAX", "5"))

try:
    pool = ConnectionPool(conninfo=DB_URL, min_size=POOL_MIN, max_size=POOL_MAX)
except Exception as e:
    raise RuntimeError(f"Unable to create DB connection pool: {e}")

logger = logging.getLogger(__name__)


def _with_registered_vector(conn):
    """
    Ensure pgvector adapter is registered. Safe even if called multiple times.
    """
    try:
        register_vector(conn)
    except Exception as e:
        logger.exception("Failed to register pgvector: %s", e)
        raise


def ensure_table() -> None:
    with pool.connection() as conn:
        _with_registered_vector(conn)
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS memories (
                        id uuid primary key default gen_random_uuid(),
                        content text,
                        embedding vector({EMBED_DIM}),
                        metadata jsonb,
                        created_at timestamptz default now()
                    );
                    """
                )

                try:
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS memories_embedding_idx "
                        "ON memories USING ivfflat (embedding) WITH (lists = 100);"
                    )
                except Exception:
                    logger.debug("ivfflat index creation failed; continuing.")

            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.exception("ensure_table failed: %s", e)
            raise


def insert_memory(
    content: str,
    embedding: List[float],
    metadata: Optional[dict] = None,
) -> None:
    if not content or not embedding:
        raise ValueError("content and embedding are required")

    with pool.connection() as conn:
        _with_registered_vector(conn)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO memories (content, embedding, metadata) "
                    "VALUES (%s, %s, %s);",
                    (content, Vector(embedding), json.dumps(metadata or {})),
                )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.exception("insert_memory failed: %s", e)
            raise


def search_memories(
    query_vector: List[float],
    top_k: int = 5,
) -> List[dict]:
    """
    Search for the nearest embeddings.
    """
    if not query_vector:
        return []

    qv = Vector(query_vector)

    with pool.connection() as conn:
        _with_registered_vector(conn)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, content, metadata, embedding <=> %s AS distance
                    FROM memories
                    ORDER BY embedding <=> %s
                    LIMIT %s;
                    """,
                    (qv, qv, top_k),
                )
                rows = cur.fetchall()
        except Exception as e:
            logger.exception("search_memories failed: %s", e)
            raise

    return [
        {
            "id": str(r[0]),
            "content": r[1],
            "metadata": r[2],
            "distance": r[3],
        }
        for r in rows
    ]
