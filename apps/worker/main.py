"""JobOS-CN Worker 入口。"""

from __future__ import annotations

import argparse
import json
import socket
from uuid import uuid4

from apps.api.dependencies import get_session_factory, get_settings
from apps.worker.scheduler import WorkerScheduler
from jobos.workflow.orchestrator import WorkflowOrchestrator
from jobos.workflow.task_queue import TaskQueue


def build_scheduler() -> WorkerScheduler:
    """创建默认 Worker 调度器。"""
    settings = get_settings()
    worker_id = f"{socket.gethostname()}-{uuid4().hex[:8]}"
    queue = TaskQueue(get_session_factory(), settings.worker.lease_seconds)
    orchestrator = WorkflowOrchestrator(queue=queue, handlers={})
    return WorkerScheduler(orchestrator, worker_id)


def main() -> None:
    """启动 Worker。"""
    parser = argparse.ArgumentParser(description="JobOS-CN 后台任务 Worker")
    parser.add_argument("--once", action="store_true", help="只轮询一次后退出")
    args = parser.parse_args()
    scheduler = build_scheduler()
    print(
        json.dumps(
            {"event": "worker.started", "worker_id": scheduler.worker_id},
            ensure_ascii=False,
        )
    )
    if args.once:
        scheduler.run_once()
    else:
        scheduler.run_forever()


if __name__ == "__main__":
    main()
