"""任务租约测试。"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, sessionmaker

from jobos.workflow.task_queue import TaskQueue


def test_two_workers_cannot_lease_same_task(factory: sessionmaker[Session]) -> None:
    queue = TaskQueue(factory, lease_seconds=60)
    task = queue.enqueue("DISCOVER_JOBS", "profile", "p1", "discover:p1")
    first = queue.lease("worker-1")
    second = queue.lease("worker-2")
    assert first is not None and first.id == task.id
    assert second is None


def test_expired_lease_is_recovered(factory: sessionmaker[Session]) -> None:
    queue = TaskQueue(factory, lease_seconds=1)
    queue.enqueue("SYNC_MESSAGES", "account", "a1", "sync:a1")
    now = datetime.now(timezone.utc)
    leased = queue.lease("worker-1", now)
    assert leased is not None
    assert queue.recover_expired(now + timedelta(seconds=2)) == 1
    assert queue.lease("worker-2", now + timedelta(seconds=2)) is not None
