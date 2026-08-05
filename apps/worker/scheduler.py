"""Worker 调度循环。"""

from __future__ import annotations

import time
from dataclasses import dataclass

from jobos.workflow.orchestrator import WorkflowOrchestrator


@dataclass
class WorkerScheduler:
    """按固定间隔执行数据库任务。"""

    orchestrator: WorkflowOrchestrator
    worker_id: str
    poll_interval_seconds: float = 1.0

    def run_once(self) -> bool:
        """执行一个任务。"""
        return self.orchestrator.execute_once(self.worker_id)

    def run_forever(self) -> None:
        """持续轮询，直到进程收到中断信号。"""
        while True:
            worked = self.run_once()
            if not worked:
                time.sleep(self.poll_interval_seconds)
