import json
import logging
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional
import sqlite_vec
from fastembed import TextEmbedding

logger = logging.getLogger("vector_memory")

# Path to the persistent vector database
DATA_DIR = os.environ.get("AGENT_DATA_DIR", "/app/data")
os.makedirs(DATA_DIR, exist_ok=True)
VECTOR_DB_PATH = os.path.join(DATA_DIR, "agent_memory.db")

# Global lazy-loaded embedding model (384-dimensional ONNX embeddings)
_embedding_model: Optional[TextEmbedding] = None


def get_embedding_model() -> TextEmbedding:
    global _embedding_model
    if _embedding_model is None:
        logger.info("Initializing FastEmbed TextEmbedding model (BAAI/bge-small-en-v1.5)...")
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _embedding_model


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(VECTOR_DB_PATH, timeout=30.0)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.row_factory = sqlite3.Row
    return conn


def init_vector_memory_db() -> None:
    """
    Initializes tables and indexes for agent vector memory.
    """
    conn = get_db_connection()
    try:
        with conn:
            # Metadata storage table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    use_count INTEGER DEFAULT 0,
                    effectiveness_score REAL DEFAULT 1.0
                );
            """)

            # Fast index on category and agent_id
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_agent ON agent_memories(agent_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_cat ON agent_memories(category);")

            # sqlite-vec virtual table for 384-dimensional cosine/distance search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS agent_vectors USING vec0(
                    memory_id INTEGER PRIMARY KEY,
                    embedding float[384]
                );
            """)
        logger.info(f"Vector memory database initialized cleanly at {VECTOR_DB_PATH}")
    finally:
        conn.close()


def store_memory(
    agent_id: str,
    content: str,
    category: str = "domain_knowledge",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Embeds and stores a new memory chunk for an agent.
    """
    if not content or not content.strip():
        return {"ok": False, "error": "Content cannot be empty"}

    content_clean = content.strip()
    model = get_embedding_model()
    embeddings = list(model.embed([content_clean]))
    vector = embeddings[0]

    meta_str = json.dumps(metadata or {})
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO agent_memories (agent_id, category, content, metadata_json)
                VALUES (?, ?, ?, ?);
                """,
                (agent_id, category, content_clean, meta_str),
            )
            memory_id = cur.lastrowid

            # Insert into vector virtual table
            serialized_vec = sqlite_vec.serialize_float32(vector)
            conn.execute(
                """
                INSERT INTO agent_vectors (memory_id, embedding)
                VALUES (?, ?);
                """,
                (memory_id, serialized_vec),
            )

        return {
            "ok": True,
            "memory_id": memory_id,
            "agent_id": agent_id,
            "category": category,
            "content": content_clean,
            "message": "Memory stored and vectorized successfully.",
        }
    except Exception as e:
        logger.error(f"Failed to store vector memory: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def query_memories(
    query: str,
    agent_id: Optional[str] = None,
    category: Optional[str] = None,
    top_k: int = 4,
) -> List[Dict[str, Any]]:
    """
    Performs semantic vector search across agent memories.
    """
    if not query or not query.strip():
        return []

    model = get_embedding_model()
    embeddings = list(model.embed([query.strip()]))
    query_vector = embeddings[0]
    serialized_q = sqlite_vec.serialize_float32(query_vector)

    conn = get_db_connection()
    try:
        # Match nearest embeddings using sqlite-vec with k constraint
        # Fetch matching memory_ids and distances first
        vec_sql = "SELECT memory_id, distance FROM agent_vectors WHERE embedding MATCH ? AND k = ?"
        vec_rows = conn.execute(vec_sql, (serialized_q, top_k * 3)).fetchall()

        if not vec_rows:
            return []

        # Map distance by memory_id
        dist_map = {r[0]: float(r[1]) for r in vec_rows}
        placeholders = ",".join("?" for _ in dist_map.keys())

        query_sql = f"""
            SELECT 
                id,
                agent_id,
                category,
                content,
                metadata_json,
                created_at,
                effectiveness_score
            FROM agent_memories
            WHERE id IN ({placeholders})
        """
        params: List[Any] = list(dist_map.keys())

        if agent_id:
            query_sql += " AND (agent_id = ? OR agent_id = 'all' OR agent_id = 'system')"
            params.append(agent_id)

        if category:
            query_sql += " AND category = ?"
            params.append(category)

        meta_rows = conn.execute(query_sql, params).fetchall()

        results = []
        for r in meta_rows:
            mem_id = r["id"]
            dist = dist_map.get(mem_id, 1.0)
            meta = {}
            try:
                if r["metadata_json"]:
                    meta = json.loads(r["metadata_json"])
            except Exception:
                pass

            sim = max(0.0, 1.0 - (dist / 2.0))
            results.append({
                "id": mem_id,
                "agent_id": r["agent_id"],
                "category": r["category"],
                "content": r["content"],
                "metadata": meta,
                "similarity": round(sim, 4),
                "distance": round(dist, 4),
                "created_at": r["created_at"],
            })

        # Sort by lowest distance
        results.sort(key=lambda x: x["distance"])
        return results[:top_k]

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []
    finally:
        conn.close()


def get_memory_stats() -> Dict[str, Any]:
    """
    Returns counts and summary breakdown of stored memories.
    """
    conn = get_db_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM agent_memories;").fetchone()[0]
        cat_counts = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM agent_memories GROUP BY category;"
        ).fetchall()
        agent_counts = conn.execute(
            "SELECT agent_id, COUNT(*) as cnt FROM agent_memories GROUP BY agent_id;"
        ).fetchall()

        return {
            "total_memories": total,
            "categories": {r["category"]: r["cnt"] for r in cat_counts},
            "by_agent": {r["agent_id"]: r["cnt"] for r in agent_counts},
        }
    except Exception as e:
        return {"total_memories": 0, "error": str(e)}
    finally:
        conn.close()


# Ensure database is initialized upon module import
try:
    init_vector_memory_db()
except Exception as init_err:
    logger.warning(f"Could not immediately init vector DB: {init_err}")
