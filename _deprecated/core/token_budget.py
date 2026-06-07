"""
Token 预算管理器 - 控制各 Agent 的 token 消耗上限
"""
from dataclasses import dataclass, field
from utils.logger import get_logger

logger = get_logger("token_budget")


@dataclass
class AgentBudget:
    agent_name: str
    max_tokens: int
    used_tokens: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

    @property
    def utilization(self) -> float:
        return self.used_tokens / self.max_tokens if self.max_tokens > 0 else 0.0


class TokenBudgetManager:
    """
    Token 预算控制器
    规则: planner ≤ 800, executor ≤ 1200, reasoner ≤ 1500, report ≤ 2000, chart ≤ 1000
    """

    DEFAULT_BUDGETS = {
        "planner": 2000,
        "executor": 2000,
        "reasoner": 3500,
        "report": 2500,
        "chart": 2000,
        "synthesizer": 3000,
    }

    def __init__(self, custom_budgets: dict[str, int] | None = None):
        budgets = {**self.DEFAULT_BUDGETS}
        if custom_budgets:
            budgets.update(custom_budgets)

        self._budgets: dict[str, AgentBudget] = {
            name: AgentBudget(agent_name=name, max_tokens=max_tok)
            for name, max_tok in budgets.items()
        }
        self._total_budget = sum(budgets.values())
        logger.info(f"TokenBudgetManager initialized: total_budget={self._total_budget}")

    def get_max_tokens(self, agent_name: str) -> int:
        """获取指定 Agent 的 max_tokens 限制"""
        budget = self._budgets.get(agent_name)
        if not budget:
            logger.warning(f"Unknown agent '{agent_name}', using default 1024")
            return 1024
        return budget.remaining

    def record_usage(self, agent_name: str, tokens_used: int):
        """记录 token 消耗"""
        budget = self._budgets.get(agent_name)
        if budget:
            budget.used_tokens += tokens_used
            logger.debug(
                f"[{agent_name}] used {tokens_used} tokens, "
                f"remaining={budget.remaining}, utilization={budget.utilization:.0%}"
            )

    def check_budget(self, agent_name: str) -> bool:
        """检查是否还有预算"""
        budget = self._budgets.get(agent_name)
        if not budget:
            return True
        return budget.remaining > 0

    def get_all_status(self) -> dict[str, dict]:
        """获取所有 Agent 的预算状态"""
        return {
            name: {
                "max_tokens": b.max_tokens,
                "used_tokens": b.used_tokens,
                "remaining": b.remaining,
                "utilization": f"{b.utilization:.0%}",
            }
            for name, b in self._budgets.items()
        }

    def reset(self):
        """重置所有预算"""
        for budget in self._budgets.values():
            budget.used_tokens = 0
        logger.info("Token budgets reset")

    @property
    def total_used(self) -> int:
        return sum(b.used_tokens for b in self._budgets.values())

    @property
    def total_budget(self) -> int:
        return self._total_budget
