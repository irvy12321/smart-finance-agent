"""Reset the default admin password from DEFAULT_ADMIN_PASSWORD.

This module is intended for production deployment/bootstrap jobs. It avoids
printing the password and can be run as:

    python -m app.ops.reset_admin_password
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import bcrypt


def reset_admin_password(username: str = "admin") -> str:
    password = os.getenv("DEFAULT_ADMIN_PASSWORD", "").strip()
    if len(password) < 12:
        raise RuntimeError(
            "DEFAULT_ADMIN_PASSWORD must be set to at least 12 characters."
        )

    # Import lazily so callers can validate environment before storage init.
    from app import storage

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )
    now = datetime.now(timezone.utc).isoformat()

    conn = storage._get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE users
                SET hashed_password = ?, role = ?, is_active = ?, updated_at = ?
                WHERE username = ?
                """,
                (hashed_password, "admin", True, now, username),
            )
            action = "updated"
        else:
            conn.execute(
                """
                INSERT INTO users
                    (username, email, hashed_password, is_active, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    "admin@sfa.local",
                    hashed_password,
                    True,
                    "admin",
                    now,
                    now,
                ),
            )
            action = "created"
        conn.commit()
    finally:
        conn.close()

    return action


def main() -> None:
    action = reset_admin_password()
    print(f"Admin user {action} from DEFAULT_ADMIN_PASSWORD.")


if __name__ == "__main__":
    main()
