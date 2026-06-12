"""
登录安全模块单元测试
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.auth.login_security import (
    MAX_FAILED_ATTEMPTS,
    LOCKOUT_DURATION_MINUTES,
    _clear_lockout,
    get_login_attempt,
    get_remaining_attempts,
    is_account_locked,
    record_login_failure,
    record_login_success,
)


@pytest.fixture
def test_username():
    """测试用户名"""
    return "test_security_user"


@pytest.fixture(autouse=True)
def cleanup(test_username):
    """测试后清理"""
    yield
    # 清理测试数据
    from app import storage
    conn = storage._get_connection()
    try:
        conn.execute("DELETE FROM login_attempts WHERE username = ?", (test_username,))
        conn.commit()
    finally:
        conn.close()


class TestLoginSecurity:
    """登录安全测试"""

    def test_initial_state(self, test_username):
        """测试初始状态"""
        is_locked, remaining = is_account_locked(test_username)
        assert is_locked is False
        assert remaining is None

        attempts = get_remaining_attempts(test_username)
        assert attempts == MAX_FAILED_ATTEMPTS

    def test_record_failure(self, test_username):
        """测试记录登录失败"""
        record_login_failure(test_username)

        attempt = get_login_attempt(test_username)
        assert attempt is not None
        assert attempt["failed_count"] == 1

        remaining = get_remaining_attempts(test_username)
        assert remaining == MAX_FAILED_ATTEMPTS - 1

    def test_lockout_after_max_failures(self, test_username):
        """测试达到最大失败次数后锁定"""
        for _ in range(MAX_FAILED_ATTEMPTS):
            record_login_failure(test_username)

        is_locked, seconds_remaining = is_account_locked(test_username)
        assert is_locked is True
        assert seconds_remaining > 0
        assert seconds_remaining <= LOCKOUT_DURATION_MINUTES * 60

    def test_success_resets_count(self, test_username):
        """测试登录成功后清零"""
        # 记录几次失败
        for _ in range(3):
            record_login_failure(test_username)

        # 登录成功
        record_login_success(test_username)

        # 验证清零
        attempt = get_login_attempt(test_username)
        assert attempt["failed_count"] == 0
        assert attempt["locked_until"] is None

        remaining = get_remaining_attempts(test_username)
        assert remaining == MAX_FAILED_ATTEMPTS

    def test_remaining_attempts_decrease(self, test_username):
        """测试剩余次数递减"""
        for i in range(MAX_FAILED_ATTEMPTS):
            remaining = get_remaining_attempts(test_username)
            assert remaining == MAX_FAILED_ATTEMPTS - i
            record_login_failure(test_username)

        remaining = get_remaining_attempts(test_username)
        assert remaining == 0
