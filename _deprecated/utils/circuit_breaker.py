"""
Circuit Breaker - 3态熔断器
CLOSED: 正常放行
OPEN: 熔断拒绝，等待恢复
HALF_OPEN: 探测恢复
"""
import time
import threading
from enum import Enum
from dataclasses import dataclass, field
from utils.logger import get_logger
from utils.exceptions import CircuitBreakerOpenError

logger = get_logger("circuit_breaker")


class BreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """单个资源的熔断器"""
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max: int = 1

    _state: BreakerState = field(default=BreakerState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _half_open_attempts: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    @property
    def state(self) -> BreakerState:
        with self._lock:
            if self._state == BreakerState.OPEN:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    self._state = BreakerState.HALF_OPEN
                    self._half_open_attempts = 0
                    logger.info(f"[{self.name}] OPEN -> HALF_OPEN (recovery timeout reached)")
            return self._state

    def allow_request(self) -> bool:
        """是否允许请求通过"""
        current = self.state
        if current == BreakerState.CLOSED:
            return True
        if current == BreakerState.HALF_OPEN:
            with self._lock:
                if self._half_open_attempts < self.half_open_max:
                    self._half_open_attempts += 1
                    return True
                return False
        return False

    def record_success(self):
        """记录成功"""
        with self._lock:
            if self._state == BreakerState.HALF_OPEN:
                self._success_count += 1
                self._state = BreakerState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info(f"[{self.name}] HALF_OPEN -> CLOSED (recovered)")
            else:
                self._failure_count = 0
                self._success_count += 1

    def record_failure(self):
        """记录失败"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == BreakerState.HALF_OPEN:
                self._state = BreakerState.OPEN
                logger.warning(f"[{self.name}] HALF_OPEN -> OPEN (probe failed)")
            elif self._failure_count >= self.failure_threshold:
                self._state = BreakerState.OPEN
                logger.warning(
                    f"[{self.name}] CLOSED -> OPEN "
                    f"(failures={self._failure_count}/{self.failure_threshold})"
                )

    def check_or_raise(self):
        """检查熔断器状态，OPEN 时抛出异常"""
        if not self.allow_request():
            remaining = self.recovery_timeout - (time.monotonic() - self._last_failure_time)
            raise CircuitBreakerOpenError(self.name, retry_after=max(0, remaining))

    def reset(self):
        """手动重置"""
        with self._lock:
            self._state = BreakerState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_attempts = 0
            logger.info(f"[{self.name}] Reset to CLOSED")

    def get_status(self) -> dict:
        """获取状态信息"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }


class CircuitBreakerManager:
    """熔断器管理器 - 每个 tool_name 独立熔断器"""
    _instance: "CircuitBreakerManager | None" = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._breakers: dict[str, CircuitBreaker] = {}
        return cls._instance

    def get_breaker(
        self,
        tool_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> CircuitBreaker:
        """获取或创建指定工具的熔断器"""
        if tool_name not in self._breakers:
            self._breakers[tool_name] = CircuitBreaker(
                name=tool_name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
            )
        return self._breakers[tool_name]

    def get_all_status(self) -> dict[str, dict]:
        """获取所有熔断器状态"""
        return {name: b.get_status() for name, b in self._breakers.items()}

    def reset_all(self):
        """重置所有熔断器"""
        for breaker in self._breakers.values():
            breaker.reset()
