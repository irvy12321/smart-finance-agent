"""
SQLite-based persistent storage for chat conversations and tasks.
Replaces the in-memory dict with a real database.
"""
import json
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "chat.db"


def _ensure_db_dir() -> Path:
    """Ensure database directory exists and is writable"""
    global DB_DIR, DB_PATH

    try:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        # Test write permission
        test_file = DB_DIR / ".write_test"
        test_file.touch()
        test_file.unlink()
        return DB_DIR
    except (PermissionError, OSError) as e:
        # Fallback to temp directory
        import warnings
        temp_dir = Path(tempfile.gettempdir()) / "smart_finance_agent"
        temp_dir.mkdir(parents=True, exist_ok=True)
        warnings.warn(
            f"Cannot write to {DB_DIR}: {e}. Using fallback: {temp_dir}",
            UserWarning,
            stacklevel=2,
        )
        DB_DIR = temp_dir
        DB_PATH = DB_DIR / "chat.db"
        return DB_DIR


def _get_connection() -> sqlite3.Connection:
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
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

            CREATE TABLE IF NOT EXISTS tasks (
                task_id         TEXT PRIMARY KEY,
                query           TEXT NOT NULL,
                priority        INTEGER DEFAULT 1,
                status          TEXT NOT NULL DEFAULT 'pending',
                progress        REAL DEFAULT 0.0,
                current_stage   TEXT DEFAULT '',
                message         TEXT DEFAULT '',
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                result_json     TEXT DEFAULT NULL,
                events_json     TEXT DEFAULT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
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


# ── Task CRUD ──────────────────────────────────────────────

def create_task(task_id: str, query: str, priority: int = 1) -> Dict[str, Any]:
    now = datetime.now().isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO tasks (task_id, query, priority, status, progress, current_stage, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (task_id, query, priority, "pending", 0.0, "", now, now),
        )
        conn.commit()
        return {
            "task_id": task_id,
            "query": query,
            "priority": priority,
            "status": "pending",
            "progress": 0.0,
            "current_stage": "",
            "message": "",
            "created_at": now,
            "updated_at": now,
            "result": None,
            "events": [],
        }
    finally:
        conn.close()


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        if row is None:
            return None
        task = dict(row)
        task["result"] = json.loads(task["result_json"]) if task["result_json"] else None
        task["events"] = json.loads(task["events_json"]) if task["events_json"] else []
        del task["result_json"]
        del task["events_json"]
        return task
    finally:
        conn.close()


def update_task(task_id: str, **kwargs) -> bool:
    conn = _get_connection()
    try:
        allowed_fields = {"status", "progress", "current_stage", "message"}
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if not updates:
            return False

        now = datetime.now().isoformat()
        updates.append("updated_at = ?")
        values.append(now)
        values.append(task_id)

        cursor = conn.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?",
            values,
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_task_result(task_id: str, result: Dict[str, Any], events: list) -> bool:
    conn = _get_connection()
    try:
        now = datetime.now().isoformat()
        cursor = conn.execute(
            "UPDATE tasks SET status = ?, progress = ?, current_stage = ?, message = ?, result_json = ?, events_json = ?, updated_at = ? WHERE task_id = ?",
            ("completed", 100.0, "completed", "Task completed successfully.", json.dumps(result), json.dumps(events), now, task_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_task_failure(task_id: str, status: str, current_stage: str, message: str) -> bool:
    conn = _get_connection()
    try:
        now = datetime.now().isoformat()
        cursor = conn.execute(
            "UPDATE tasks SET status = ?, current_stage = ?, message = ?, updated_at = ? WHERE task_id = ?",
            (status, current_stage, message, now, task_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def list_tasks() -> List[Dict[str, Any]]:
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT task_id, query, status, created_at, updated_at FROM tasks ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
