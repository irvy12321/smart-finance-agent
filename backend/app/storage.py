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
from typing import Any

DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "chat.db"


_db_dir_checked = False


def _ensure_db_dir() -> Path:
    """Ensure database directory exists and is writable.

    The writability probe uses a per-process unique filename and runs only
    once. A shared probe filename races across uvicorn workers: one worker's
    unlink removes the file another worker just created, raising a spurious
    FileNotFoundError. That made a worker fall back to an empty temp DB and
    return 500 ("no such table: users") on every authenticated request.
    """
    global DB_DIR, DB_PATH, _db_dir_checked

    if _db_dir_checked:
        return DB_DIR

    try:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        # Per-process probe name avoids cross-worker races on a shared file
        test_file = DB_DIR / f".write_test_{os.getpid()}"
        test_file.touch()
        test_file.unlink(missing_ok=True)
        _db_dir_checked = True
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
        _db_dir_checked = True
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
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                username        TEXT NOT NULL UNIQUE,
                email           TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                is_active       BOOLEAN DEFAULT 1,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                user_id         INTEGER DEFAULT NULL,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
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
                user_id         INTEGER DEFAULT NULL,
                query           TEXT NOT NULL,
                priority        INTEGER DEFAULT 1,
                status          TEXT NOT NULL DEFAULT 'pending',
                progress        REAL DEFAULT 0.0,
                current_stage   TEXT DEFAULT '',
                message         TEXT DEFAULT '',
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                result_json     TEXT DEFAULT NULL,
                events_json     TEXT DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                token_hash      TEXT NOT NULL UNIQUE,
                expires_at      TEXT NOT NULL,
                revoked         BOOLEAN DEFAULT 0,
                created_at      TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
            CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
            CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

            CREATE TABLE IF NOT EXISTS login_attempts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                username        TEXT NOT NULL,
                failed_count    INTEGER DEFAULT 0,
                last_failed_at  TEXT DEFAULT NULL,
                locked_until    TEXT DEFAULT NULL,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                UNIQUE(username)
            );
            CREATE INDEX IF NOT EXISTS idx_login_attempts_username ON login_attempts(username);

            CREATE TABLE IF NOT EXISTS llm_call_logs (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id          TEXT DEFAULT '',
                agent_name        TEXT NOT NULL,
                model             TEXT NOT NULL,
                prompt            TEXT DEFAULT '',
                response          TEXT DEFAULT '',
                prompt_tokens     INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens      INTEGER DEFAULT 0,
                latency_ms        REAL DEFAULT 0,
                status            TEXT DEFAULT 'ok',
                error             TEXT DEFAULT '',
                created_at        TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_llm_call_logs_trace ON llm_call_logs(trace_id);

            CREATE TABLE IF NOT EXISTS event_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id    TEXT DEFAULT '',
                event_type  TEXT NOT NULL,
                agent_name  TEXT NOT NULL,
                data_json   TEXT DEFAULT '{}',
                created_at  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_event_log_trace ON event_log(trace_id);

            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id      INTEGER PRIMARY KEY,
                profile_json TEXT NOT NULL DEFAULT '{}',
                updated_at   TEXT NOT NULL
            );
        """)

        # Migrate existing tables: add user_id column if missing
        _migrate_add_column(conn, "conversations", "user_id", "INTEGER DEFAULT NULL")
        _migrate_add_column(conn, "tasks", "user_id", "INTEGER DEFAULT NULL")

        # Migrate users table: add role column if missing
        _migrate_add_column(conn, "users", "role", "TEXT NOT NULL DEFAULT 'viewer'")

        # Create default admin user if not exists
        _create_default_admin(conn)

        conn.commit()
    finally:
        conn.close()


def _migrate_add_column(
    conn: sqlite3.Connection, table: str, column: str, col_type: str
) -> None:
    """Add a column to a table if it doesn't already exist"""
    try:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except Exception:
        pass


def _create_default_admin(conn: sqlite3.Connection) -> None:
    """Create default admin user if not exists"""
    import bcrypt

    # Check if admin user exists
    cursor = conn.execute("SELECT id, role FROM users WHERE username = 'admin'")
    existing = cursor.fetchone()
    if existing:
        # Self-heal: an admin row created before the RBAC migration gets the
        # column default ('viewer') and would otherwise stay non-admin forever.
        if existing[1] != "admin":
            conn.execute(
                "UPDATE users SET role = 'admin', updated_at = ? WHERE username = 'admin'",
                (datetime.now().isoformat(),),
            )
        return

    # Create default admin user
    now = datetime.now().isoformat()
    default_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "")
    generated = False
    if not default_password:
        # Never fall back to a hard-coded/weak password. Generate a strong
        # one-time password and surface it once so it can be rotated.
        import secrets

        default_password = secrets.token_urlsafe(18)
        generated = True
    hashed_password = bcrypt.hashpw(
        default_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    conn.execute(
        """INSERT INTO users (username, email, hashed_password, is_active, role, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("admin", "admin@sfa.local", hashed_password, True, "admin", now, now),
    )
    if generated:
        print(
            "[WARN] DEFAULT_ADMIN_PASSWORD not set. Generated a random admin password "
            f"(username: admin, password: {default_password}). "
            "Store it now and rotate it; it will NOT be shown again."
        )
    else:
        print(
            "[INFO] Default admin user created (username: admin) using DEFAULT_ADMIN_PASSWORD."
        )


# Initialize on import
init_db()


# ── Conversation CRUD ──────────────────────────────────────


def create_conversation(
    conversation_id: str, user_id: int | None = None
) -> dict[str, Any]:
    now = datetime.now().isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO conversations (conversation_id, user_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conversation_id, user_id, now, now),
        )
        conn.commit()
        return {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }
    finally:
        conn.close()


def get_conversation(conversation_id: str) -> dict[str, Any] | None:
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


def list_conversations(user_id: int | None = None) -> list[dict[str, Any]]:
    conn = _get_connection()
    try:
        if user_id is not None:
            rows = conn.execute(
                "SELECT conversation_id, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT conversation_id, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
            ).fetchall()
        result = []
        for row in rows:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?",
                (row["conversation_id"],),
            ).fetchone()
            result.append(
                {
                    "conversation_id": row["conversation_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "message_count": count["cnt"],
                }
            )
        return result
    finally:
        conn.close()


def get_task_owner(task_id: str) -> int | None:
    """Return the user_id that owns a task, or None if not found."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT user_id FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        return row["user_id"] if row else None
    finally:
        conn.close()


def get_conversation_owner(conversation_id: str) -> int | None:
    """Return the user_id that owns a conversation, or None if not found."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT user_id FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        return row["user_id"] if row else None
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


def add_message(conversation_id: str, role: str, content: str) -> dict[str, Any]:
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


def create_task(
    task_id: str, query: str, priority: int = 1, user_id: int | None = None
) -> dict[str, Any]:
    now = datetime.now().isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO tasks (task_id, user_id, query, priority, status, progress, current_stage, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task_id, user_id, query, priority, "pending", 0.0, "", now, now),
        )
        conn.commit()
        return {
            "task_id": task_id,
            "user_id": user_id,
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


def get_task(task_id: str) -> dict[str, Any] | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        if row is None:
            return None
        task = dict(row)
        task["result"] = (
            json.loads(task["result_json"]) if task["result_json"] else None
        )
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


def update_task_result(task_id: str, result: dict[str, Any], events: list) -> bool:
    conn = _get_connection()
    try:
        now = datetime.now().isoformat()
        cursor = conn.execute(
            "UPDATE tasks SET status = ?, progress = ?, current_stage = ?, message = ?, result_json = ?, events_json = ?, updated_at = ? WHERE task_id = ?",
            (
                "completed",
                100.0,
                "completed",
                "Task completed successfully.",
                json.dumps(result),
                json.dumps(events),
                now,
                task_id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_task_failure(
    task_id: str, status: str, current_stage: str, message: str
) -> bool:
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


def fail_interrupted_running_tasks() -> int:
    """Mark in-progress tasks as failed after a process restart.

    Background research work lives in the FastAPI process. If the process is
    restarted by uvicorn reload or deployment, those tasks cannot resume safely,
    so leaving them as ``running`` makes the UI poll forever and report fetches
    return 400.
    """
    conn = _get_connection()
    try:
        now = datetime.now().isoformat()
        cursor = conn.execute(
            """
            UPDATE tasks
            SET status = ?,
                current_stage = ?,
                message = ?,
                updated_at = ?
            WHERE status = ?
            """,
            (
                "failed",
                "interrupted",
                "Task was interrupted by a backend restart. Please start a new research task.",
                now,
                "running",
            ),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def list_tasks(user_id: int | None = None) -> list[dict[str, Any]]:
    conn = _get_connection()
    try:
        if user_id is not None:
            rows = conn.execute(
                "SELECT task_id, query, status, created_at, updated_at FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT task_id, query, status, created_at, updated_at FROM tasks ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ── Memory: user profiles ──────────────────────────────


def get_user_profile(user_id: int) -> dict[str, Any] | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT profile_json FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["profile_json"] or "{}")
    finally:
        conn.close()


def upsert_user_profile(user_id: int, profile: dict[str, Any]) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO user_profiles (user_id, profile_json, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 profile_json = excluded.profile_json,
                 updated_at = excluded.updated_at""",
            (
                user_id,
                json.dumps(profile, ensure_ascii=False, default=str),
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ── Observability: LLM call logs + event log ──────────────


def insert_llm_call_log(
    trace_id: str,
    agent_name: str,
    model: str,
    prompt: str,
    response: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    latency_ms: float = 0.0,
    status: str = "ok",
    error: str = "",
) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO llm_call_logs
               (trace_id, agent_name, model, prompt, response,
                prompt_tokens, completion_tokens, total_tokens,
                latency_ms, status, error, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trace_id,
                agent_name,
                model,
                prompt,
                response,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                latency_ms,
                status,
                error,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_llm_call_logs(
    trace_id: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    conn = _get_connection()
    try:
        if trace_id:
            rows = conn.execute(
                "SELECT * FROM llm_call_logs WHERE trace_id = ? ORDER BY id DESC LIMIT ?",
                (trace_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM llm_call_logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def insert_event_log(
    trace_id: str, event_type: str, agent_name: str, data: dict[str, Any]
) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO event_log (trace_id, event_type, agent_name, data_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                trace_id,
                event_type,
                agent_name,
                json.dumps(data, ensure_ascii=False, default=str),
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_event_logs(
    trace_id: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    conn = _get_connection()
    try:
        if trace_id:
            rows = conn.execute(
                "SELECT * FROM event_log WHERE trace_id = ? ORDER BY id DESC LIMIT ?",
                (trace_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM event_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["data"] = json.loads(item.pop("data_json") or "{}")
            result.append(item)
        return result
    finally:
        conn.close()
