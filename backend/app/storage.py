"""
SQLite-based persistent storage for chat conversations.
Replaces the in-memory dict with a real database.
"""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "chat.db"


def _get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = _get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role            TEXT NOT NULL,
                content         TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
        """)
        conn.commit()
    finally:
        conn.close()


# Initialize on import
init_db()


# ── Conversation CRUD ──────────────────────────────────────

def create_conversation(conversation_id: str) -> Dict[str, Any]:
    now = datetime.now().isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO conversations (conversation_id, created_at, updated_at) VALUES (?, ?, ?)",
            (conversation_id, now, now),
        )
        conn.commit()
        return {"conversation_id": conversation_id, "created_at": now, "updated_at": now, "messages": []}
    finally:
        conn.close()


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT conversation_id, created_at, updated_at FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        if row is None:
            return None
        messages = conn.execute(
            "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
        return {
            "conversation_id": row["conversation_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "messages": [dict(m) for m in messages],
        }
    finally:
        conn.close()


def list_conversations() -> List[Dict[str, Any]]:
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT conversation_id, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
        result = []
        for row in rows:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?",
                (row["conversation_id"],),
            ).fetchone()
            result.append({
                "conversation_id": row["conversation_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "message_count": count["cnt"],
            })
        return result
    finally:
        conn.close()


def delete_conversation(conversation_id: str) -> bool:
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def add_message(conversation_id: str, role: str, content: str) -> Dict[str, Any]:
    now = datetime.now().isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
            (now, conversation_id),
        )
        conn.commit()
        return {"role": role, "content": content, "timestamp": now}
    finally:
        conn.close()
