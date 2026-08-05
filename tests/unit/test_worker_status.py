"""Worker 心跳状态测试。"""

from datetime import UTC, datetime, timedelta

from jobos.workflow.worker_status import (
    read_worker_status,
    worker_heartbeat_path,
    write_worker_heartbeat,
)


def test_worker_heartbeat_reports_online(tmp_path) -> None:
    """新鲜心跳应报告 Worker 在线。"""
    now = datetime(2026, 8, 6, 2, 0, tzinfo=UTC)
    path = worker_heartbeat_path(tmp_path)

    write_worker_heartbeat(path, "worker-test", "waiting", now=now)
    status = read_worker_status(path, 90, now=now + timedelta(seconds=30))

    assert status.online is True
    assert status.worker_id == "worker-test"
    assert status.status == "waiting"
    assert status.health_payload()["worker"] == "online"


def test_worker_heartbeat_reports_offline_when_stale(tmp_path) -> None:
    """过期心跳应报告 Worker 离线。"""
    now = datetime(2026, 8, 6, 2, 0, tzinfo=UTC)
    path = worker_heartbeat_path(tmp_path)

    write_worker_heartbeat(path, "worker-test", "working", now=now)
    status = read_worker_status(path, 90, now=now + timedelta(seconds=91))

    assert status.online is False
    assert status.worker_id == "worker-test"
    assert status.status == "offline"


def test_missing_worker_heartbeat_reports_offline(tmp_path) -> None:
    """不存在心跳文件时应报告离线。"""
    status = read_worker_status(worker_heartbeat_path(tmp_path), 90)

    assert status.online is False
    assert status.worker_id == "unknown"
    assert status.status == "offline"
