"""基于数据库租约的任务队列。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast

from sqlalchemy import and_, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from jobos.core.enums import TaskStatus
from jobos.core.errors import ConflictError, NotFoundError
from jobos.infrastructure.db.models import WorkflowTaskORM
from jobos.workflow.retry import RetryPolicy


def utc_now() -> datetime:
    """返回 UTC 时间。"""
    return datetime.now(timezone.utc)


class TaskQueue:
    """支持租约、心跳、恢复和幂等的任务队列。"""

    def __init__(self, factory: sessionmaker[Session], lease_seconds: int = 300) -> None:
        self.factory = factory
        self.lease_seconds = lease_seconds

    def enqueue(
        self,
        task_type: str,
        entity_type: str,
        entity_id: str,
        idempotency_key: str,
        input_data: dict[str, Any] | None = None,
        priority: int = 0,
        max_attempts: int = 3,
        available_at: datetime | None = None,
    ) -> WorkflowTaskORM:
        """创建任务；同一幂等键只保留一个任务。"""
        with self.factory() as session, session.begin():
            existing = session.scalar(
                select(WorkflowTaskORM).where(WorkflowTaskORM.idempotency_key == idempotency_key)
            )
            if existing is not None:
                return existing
            task = WorkflowTaskORM(
                task_type=task_type,
                entity_type=entity_type,
                entity_id=entity_id,
                idempotency_key=idempotency_key,
                input_json=input_data or {},
                priority=priority,
                max_attempts=max_attempts,
                available_at=available_at or utc_now(),
            )
            session.add(task)
            try:
                session.flush()
            except IntegrityError as exc:
                raise ConflictError(f"任务幂等键冲突：{idempotency_key}") from exc
            return task

    def lease(self, worker_id: str, now: datetime | None = None) -> WorkflowTaskORM | None:
        """原子领取一个当前可执行任务。"""
        current = now or utc_now()
        expires = current + timedelta(seconds=self.lease_seconds)
        with self.factory() as session, session.begin():
            candidate_id = session.scalar(
                select(WorkflowTaskORM.id)
                .where(
                    WorkflowTaskORM.status.in_(
                        [TaskStatus.PENDING.value, TaskStatus.RETRY_WAIT.value]
                    ),
                    WorkflowTaskORM.available_at <= current,
                    or_(
                        WorkflowTaskORM.lease_expires_at.is_(None),
                        WorkflowTaskORM.lease_expires_at <= current,
                    ),
                )
                .order_by(WorkflowTaskORM.priority.desc(), WorkflowTaskORM.created_at.asc())
                .limit(1)
            )
            if candidate_id is None:
                return None
            result = cast(
                CursorResult[Any],
                session.execute(
                    update(WorkflowTaskORM)
                    .where(
                        WorkflowTaskORM.id == candidate_id,
                        WorkflowTaskORM.status.in_(
                            [TaskStatus.PENDING.value, TaskStatus.RETRY_WAIT.value]
                        ),
                        or_(
                            WorkflowTaskORM.lease_expires_at.is_(None),
                            WorkflowTaskORM.lease_expires_at <= current,
                        ),
                    )
                    .values(
                        status=TaskStatus.LEASED.value,
                        lease_owner=worker_id,
                        lease_expires_at=expires,
                        attempt_count=WorkflowTaskORM.attempt_count + 1,
                    )
                ),
            )
            if result.rowcount != 1:
                return None
            return session.get(WorkflowTaskORM, candidate_id)

    def start(self, task_id: str, worker_id: str) -> WorkflowTaskORM:
        """把已领取任务标记为运行中。"""
        with self.factory() as session, session.begin():
            task = self._owned_task(session, task_id, worker_id)
            task.status = TaskStatus.RUNNING.value
            return task

    def heartbeat(self, task_id: str, worker_id: str, now: datetime | None = None) -> None:
        """延长任务租约。"""
        current = now or utc_now()
        with self.factory() as session, session.begin():
            task = self._owned_task(session, task_id, worker_id)
            task.lease_expires_at = current + timedelta(seconds=self.lease_seconds)

    def succeed(self, task_id: str, worker_id: str, output: dict[str, Any] | None = None) -> None:
        """完成任务并释放租约。"""
        with self.factory() as session, session.begin():
            task = self._owned_task(session, task_id, worker_id)
            task.status = TaskStatus.SUCCEEDED.value
            task.output_json = output or {}
            task.lease_owner = None
            task.lease_expires_at = None

    def fail(
        self,
        task_id: str,
        worker_id: str,
        error: str,
        policy: RetryPolicy | None = None,
        manual_required: bool = False,
    ) -> None:
        """按策略进入重试、失败或人工处理。"""
        retry_policy = policy or RetryPolicy()
        with self.factory() as session, session.begin():
            task = self._owned_task(session, task_id, worker_id)
            task.last_error = error
            task.lease_owner = None
            task.lease_expires_at = None
            if manual_required:
                task.status = TaskStatus.MANUAL_REQUIRED.value
            elif task.attempt_count >= min(task.max_attempts, retry_policy.max_attempts):
                task.status = TaskStatus.FAILED.value
            else:
                task.status = TaskStatus.RETRY_WAIT.value
                task.available_at = utc_now() + timedelta(
                    seconds=retry_policy.delay_seconds(task.attempt_count)
                )

    def recover_expired(self, now: datetime | None = None) -> int:
        """回收 Worker 崩溃后留下的过期租约。"""
        current = now or utc_now()
        with self.factory() as session, session.begin():
            result = cast(
                CursorResult[Any],
                session.execute(
                    update(WorkflowTaskORM)
                    .where(
                        WorkflowTaskORM.status.in_(
                            [TaskStatus.LEASED.value, TaskStatus.RUNNING.value]
                        ),
                        WorkflowTaskORM.lease_expires_at.is_not(None),
                        WorkflowTaskORM.lease_expires_at <= current,
                    )
                    .values(
                        status=TaskStatus.RETRY_WAIT.value,
                        lease_owner=None,
                        lease_expires_at=None,
                        available_at=current,
                    )
                ),
            )
            return int(result.rowcount or 0)

    def cancel(self, task_id: str) -> None:
        """取消尚未完成的任务。"""
        with self.factory() as session, session.begin():
            task = session.get(WorkflowTaskORM, task_id)
            if task is None:
                raise NotFoundError(f"任务不存在：{task_id}")
            task.status = TaskStatus.CANCELLED.value
            task.lease_owner = None
            task.lease_expires_at = None

    @staticmethod
    def _owned_task(session: Session, task_id: str, worker_id: str) -> WorkflowTaskORM:
        task = session.scalar(
            select(WorkflowTaskORM).where(
                and_(
                    WorkflowTaskORM.id == task_id,
                    WorkflowTaskORM.lease_owner == worker_id,
                )
            )
        )
        if task is None:
            raise NotFoundError(f"任务不存在或不属于 Worker：{task_id}")
        return task
