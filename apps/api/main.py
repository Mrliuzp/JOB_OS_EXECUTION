"""JobOS-CN FastAPI 入口。"""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from apps.api.dependencies import get_settings
from apps.api.routes import (
    analytics,
    applications,
    conversations,
    jobs,
    profile,
    providers,
    resumes,
    workflow,
)
from jobos.workflow.worker_status import read_worker_status, worker_heartbeat_path


class HealthResponse(BaseModel):
    """公开健康检查响应。"""

    status: str
    service: str


def create_app() -> FastAPI:
    """创建 API 应用。"""
    application = FastAPI(
        title="JobOS-CN API",
        version="0.2.0",
        description="本地优先、可审计的 AI 求职操作系统 API。",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-JobOS-Local"],
    )
    application.include_router(profile.router)
    application.include_router(jobs.router)
    application.include_router(applications.router)
    application.include_router(conversations.router)
    application.include_router(providers.router)
    application.include_router(resumes.router)
    application.include_router(workflow.router)
    application.include_router(analytics.router)

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        """返回进程健康状态，不访问外部服务。"""
        return HealthResponse(status="ok", service="jobos-api")

    @application.websocket("/api/v1/ws/worker-status")
    async def worker_status(websocket: WebSocket) -> None:
        """发送 Worker 真实心跳状态。"""
        await websocket.accept()
        settings = get_settings()
        heartbeat_path = worker_heartbeat_path(settings.resolved_data_dir())
        stale_after_seconds = float(settings.worker.heartbeat_seconds * 3)
        try:
            while True:
                status = read_worker_status(heartbeat_path, stale_after_seconds)
                await websocket.send_json(status.websocket_payload())
                await asyncio.sleep(5)
        except WebSocketDisconnect:
            return

    return application


app = create_app()
