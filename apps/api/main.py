"""FastAPI entry point for JobOS-CN."""

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Public health-check response."""

    status: str
    service: str


app = FastAPI(
    title="JobOS-CN API",
    version="0.1.0",
    description="Local-first AI job search operating system API.",
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Return process health without touching external dependencies."""
    return HealthResponse(status="ok", service="jobos-api")
