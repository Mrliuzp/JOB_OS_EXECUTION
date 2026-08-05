"""Worker 调度循环。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Thread

from jobos.workflow.orchestrator import WorkflowOrchestrator
from jobos.workflow.worker_status import write_worker_heartbeat


@dataclass
class WorkerScheduler:
    """按固定间隔执行数据库任务。"""

    orchestrator: WorkflowOrchestrator
    worker_id: str
    poll_interval_seconds: float = 1.0
    heartbeat_path: Path | None = None
    heartbeat_interval_seconds: float = 30.0
    _current_status: str = field(default="starting", init=False, repr=False)
    _heartbeat_thread: Thread | None = field(default=None, init=False, repr=False)

    def run_once(self) -> bool:
        """执行一个任务并更新可观测状态。"""
        self._current_status = "working"
        try:
            return self.orchestrator.execute_once(self.worker_id)
        finally:
            self._current_status = "waiting"
            self._write_heartbeat()

    def run_forever(self) -> None:
        """持续轮询，直到进程收到中断信号。"""
        self._current_status = "waiting"
        self._write_heartbeat()
        self._start_heartbeat_thread()
        while True:
            worked = self.run_once()
            if not worked:
                time.sleep(self.poll_interval_seconds)

    def _start_heartbeat_thread(self) -> None:
        """启动后台心跳线程。"""
        if self.heartbeat_path is None:
            return
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_thread = Thread(
            target=self._heartbeat_loop,
            name=f"jobos-heartbeat-{self.worker_id}",
            daemon=True,
        )
        self._heartbeat_thread.start()

    def _heartbeat_loop(self) -> None:
        """按配置间隔持续刷新心跳。"""
        while True:
            self._write_heartbeat()
            time.sleep(self.heartbeat_interval_seconds)

    def _write_heartbeat(self) -> None:
        """写入当前 Worker 状态。"""
        if self.heartbeat_path is None:
            return
        write_worker_heartbeat(
            self.heartbeat_path,
            self.worker_id,
            self._current_status,
        )
