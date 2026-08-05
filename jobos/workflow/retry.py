"""重试退避策略。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """指数退避策略。"""

    max_attempts: int = 3
    base_seconds: int = 5
    max_seconds: int = 300

    def delay_seconds(self, attempt_count: int) -> int:
        """计算第 N 次失败后的等待时间。"""
        if attempt_count < 1:
            return 0
        return min(self.base_seconds * (2 ** (attempt_count - 1)), self.max_seconds)
