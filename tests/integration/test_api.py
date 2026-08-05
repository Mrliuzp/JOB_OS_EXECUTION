"""FastAPI 关键流程测试。"""

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from apps.api.dependencies import get_session, get_settings
from apps.api.main import create_app
from jobos.core.config.settings import JobOSSettings


def test_health_profile_job_and_approval_api(factory: sessionmaker[Session]) -> None:
    app = create_app()

    def session_override() -> Generator[Session, None, None]:
        with factory() as session:
            yield session
            session.commit()

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: JobOSSettings()
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok", "service": "jobos-api"}
    profile = client.put("/api/v1/profile", json={"name": "测试用户"})
    assert profile.status_code == 200
    profile_id = profile.json()["id"]
    fact = client.post(
        "/api/v1/profile/facts",
        json={"fact_type": "skill", "statement": "熟悉 Python"},
    )
    assert fact.status_code == 200
    job = client.post(
        "/api/v1/jobs/import-text",
        json={
            "title": "Python 兼职",
            "company_name": "示例科技",
            "description": "远程兼职，要求 Python",
        },
    )
    assert job.status_code == 200
    job_id = job.json()["job"]["id"]
    application = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "profile_id": profile_id, "automation_level": "L1"},
    )
    assert application.status_code == 200
    assert client.get("/api/v1/analytics/summary").status_code == 200
