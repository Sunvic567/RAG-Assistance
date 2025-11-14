import os
import json
import logging
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))
TENANCY_MODE = os.getenv("TENANCY_MODE", "multi").lower()  # "multi" or "single"

if TENANCY_MODE not in ("single", "multi"):
    raise ValueError("TENANCY_MODE must be 'single' or 'multi'")

if not DB_URL or not DB_URL.startswith(("postgres://", "postgresql://")):
    raise RuntimeError(
        "SUPABASE_DB_URL must be a Postgres DSN (postgres://... or postgresql://...). "
        "Set SUPABASE_DB_URL in your .env with the Postgres connection string from Supabase."
    )

# DB dependencies
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


def _with_registered_vector(conn) -> None:
    """
    Ensure pgvector adapter is registered on the given psycopg connection.
    Safe to call multiple times.
    """
    try:
        register_vector(conn, dim=EMBED_DIM)
    except Exception as e:
        logger.exception("Failed to register pgvector on connection: %s", e)
        raise


def ensure_table() -> None:
    """
    Create schema depending on TENANCY_MODE.
    multi-tenant: adds tenant_id
    single-tenant: no tenant_id
    """
    with pool.connection() as conn:
        _with_registered_vector(conn)
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                if TENANCY_MODE == "multi":
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS memories (
                            id uuid primary key default gen_random_uuid(),
                            tenant_id uuid not null,
                            content text,
                            embedding vector({EMBED_DIM}),
                            metadata jsonb,
                            created_at timestamptz default now()
                        );
                        """
                    )
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_mem_tenant ON memories(tenant_id);")
                else:  # single-tenant
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

                # Try to create ANN index; non-fatal if it fails
                try:
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS memories_embedding_idx "
                        "ON memories USING ivfflat (embedding) WITH (lists = 100);"
                    )
                except Exception:
                    logger.debug("ivfflat index not created — continuing.")

            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.exception("ensure_table failed: %s", e)
            raise


def insert_memory(
    content: str,
    embedding: List[float],
    metadata: Optional[dict] = None,
    tenant_id: Optional[str] = None,
) -> None:
    """
    Multi-tenant: tenant_id REQUIRED
    Single-tenant: tenant_id ignored
    """
    if not content or not embedding:
        raise ValueError("content and embedding are required")

    if TENANCY_MODE == "multi" and not tenant_id:
        raise ValueError("tenant_id is required in multi-tenant mode")

    with pool.connection() as conn:
        _with_registered_vector(conn)
        try:
            with conn.cursor() as cur:
                if TENANCY_MODE == "multi":
                    cur.execute(
                        "INSERT INTO memories (tenant_id, content, embedding, metadata) "
                        "VALUES (%s, %s, %s, %s);",
                        (tenant_id, content, Vector(embedding), json.dumps(metadata or {})),
                    )
                else:
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
    tenant_id: Optional[str] = None,
) -> List[dict]:
    """
    Search memories using pgvector; returns list of dicts with id, content, metadata, distance.
    """
    if not query_vector:
        return []

    if TENANCY_MODE == "multi" and not tenant_id:
        raise ValueError("tenant_id is required in multi-tenant search")

    qv = Vector(query_vector)

    with pool.connection() as conn:
        _with_registered_vector(conn)
        try:
            with conn.cursor() as cur:
                if TENANCY_MODE == "multi":
                    cur.execute(
                        """
                        SELECT id, content, metadata, embedding <=> %s AS distance
                        FROM memories
                        WHERE tenant_id = %s
                        ORDER BY embedding <=> %s
                        LIMIT %s;
                        """,
                        (qv, tenant_id, qv, top_k),
                    )
                else:
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
