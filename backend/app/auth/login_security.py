"""
登录安全模块 - 暴力破解防护

功能:
- 跟踪登录失败次数
- 账户锁定机制
- 登录成功后自动清零
"""
from datetime import datetime, timedelta, timezone

from app import storage
from app.utils.logger import get_logger

logger = get_logger("login_security")

# 配置
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def _get_now() -> str:
    """获取当前 UTC 时间的 ISO 格式字符串"""
    return datetime.now(timezone.utc).isoformat()


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """解析 ISO 格式时间字符串"""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        # 确保有时区信息
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def get_login_attempt(username: str) -> dict | None:
    """获取登录尝试记录"""
    conn = storage._get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM login_attempts WHERE username = ?",
            (username,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_or_update_login_attempt(username: str, failed: bool) -> dict:
    """
    创建或更新登录尝试记录
    
    Args:
        username: 用户名
        failed: 是否失败
    
    Returns:
        更新后的记录
    """
    now = _get_now()
    conn = storage._get_connection()
    try:
        # 检查是否存在记录
        existing = conn.execute(
            "SELECT * FROM login_attempts WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            if failed:
                # 增加失败次数
                new_count = existing["failed_count"] + 1
                locked_until = None
                if new_count >= MAX_FAILED_ATTEMPTS:
                    locked_until = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)).isoformat()
                
                conn.execute(
                    """UPDATE login_attempts 
                       SET failed_count = ?, last_failed_at = ?, locked_until = ?, updated_at = ?
                       WHERE username = ?""",
                    (new_count, now, locked_until, now, username)
                )
            else:
                # 登录成功，清零
                conn.execute(
                    """UPDATE login_attempts 
                       SET failed_count = 0, last_failed_at = NULL, locked_until = NULL, updated_at = ?
                       WHERE username = ?""",
                    (now, username)
                )
            conn.commit()
        else:
            if failed:
                # 创建新记录
                locked_until = None
                if MAX_FAILED_ATTEMPTS <= 1:
                    locked_until = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)).isoformat()
                
                conn.execute(
                    """INSERT INTO login_attempts (username, failed_count, last_failed_at, locked_until, created_at, updated_at)
                       VALUES (?, 1, ?, ?, ?, ?)""",
                    (username, now, locked_until, now, now)
                )
                conn.commit()

        # 返回更新后的记录
        return get_login_attempt(username) or {"username": username, "failed_count": 0}
    finally:
        conn.close()


def is_account_locked(username: str) -> tuple[bool, int | None]:
    """
    检查账户是否被锁定
    
    Returns:
        (is_locked, seconds_remaining)
    """
    attempt = get_login_attempt(username)
    if not attempt:
        return False, None

    locked_until = _parse_datetime(attempt.get("locked_until"))
    if not locked_until:
        return False, None

    now = datetime.now(timezone.utc)
    if now < locked_until:
        remaining = int((locked_until - now).total_seconds())
        return True, remaining
    else:
        # 锁定已过期，清除锁定状态
        _clear_lockout(username)
        return False, None


def _clear_lockout(username: str) -> None:
    """清除账户锁定状态"""
    now = _get_now()
    conn = storage._get_connection()
    try:
        conn.execute(
            """UPDATE login_attempts 
               SET locked_until = NULL, updated_at = ?
               WHERE username = ?""",
            (now, username)
        )
        conn.commit()
    finally:
        conn.close()


def record_login_failure(username: str) -> dict:
    """记录登录失败"""
    return create_or_update_login_attempt(username, failed=True)


def record_login_success(username: str) -> None:
    """记录登录成功，清零失败次数"""
    create_or_update_login_attempt(username, failed=False)
    logger.info(f"Login success for {username}, failure count reset")


def get_remaining_attempts(username: str) -> int:
    """获取剩余尝试次数"""
    attempt = get_login_attempt(username)
    if not attempt:
        return MAX_FAILED_ATTEMPTS
    return max(0, MAX_FAILED_ATTEMPTS - attempt["failed_count"])


def cleanup_expired_lockouts() -> int:
    """清理过期的锁定记录"""
    now = _get_now()
    conn = storage._get_connection()
    try:
        cursor = conn.execute(
            """UPDATE login_attempts 
               SET locked_until = NULL, updated_at = ?
               WHERE locked_until IS NOT NULL AND locked_until < ?""",
            (now, now)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
