"""工作流编排器。"""

from dataclasses import dataclass
from typing import Any, Protocol

from jobos.workflow.task_queue import TaskQueue


class TaskHandler(Protocol):
    """任务处理器协议。"""

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class WorkflowOrchestrator:
    """按任务类型分发确定性处理器。"""

    queue: TaskQueue
    handlers: dict[str, TaskHandler]

    def register(self, task_type: str, handler: TaskHandler) -> None:
        """注册任务处理器。"""
        self.handlers[task_type] = handler

    def execute_once(self, worker_id: str) -> bool:
        """领取并执行一个任务。"""
        task = self.queue.lease(worker_id)
        if task is None:
            return False
        self.queue.start(task.id, worker_id)
        handler = self.handlers.get(task.task_type)
        if handler is None:
            self.queue.fail(task.id, worker_id, f"未注册任务处理器：{task.task_type}")
            return True
        try:
            output = handler(task.input_json)
        except (ValueError, RuntimeError) as exc:
            self.queue.fail(task.id, worker_id, str(exc))
        else:
            self.queue.succeed(task.id, worker_id, output)
        return True
