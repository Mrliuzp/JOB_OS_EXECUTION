"""职位导入、标准化和去重服务。"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.orm import Session

from jobos.domain.schemas import RawJobDetail
from jobos.infrastructure.db.models import JobORM
from jobos.infrastructure.repositories import JobRepository


class JobService:
    """将 Provider 或人工输入转换为标准职位。"""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.jobs = JobRepository(session)

    def import_detail(self, provider: str, detail: RawJobDetail) -> tuple[JobORM, bool]:
        """导入职位详情；返回职位和是否新建。"""
        canonical_url = canonicalize_url(detail.canonical_url)
        existing = self.jobs.find_external(provider, detail.external_job_id) or self.jobs.find_url(
            provider, canonical_url
        )
        normalized = normalize_description(detail.description)
        content_hash = hashlib.sha256(
            f"{detail.title}|{detail.company_name}|{normalized}".encode("utf-8")
        ).hexdigest()
        if existing is not None:
            existing.title = detail.title
            existing.company_name = detail.company_name
            existing.location = detail.location
            existing.work_mode = detail.work_mode
            existing.employment_type = detail.employment_type
            existing.description_raw = detail.description
            existing.description_normalized = normalized
            existing.requirements_json = detail.requirements
            existing.benefits_json = detail.benefits
            existing.salary_min = detail.salary_min
            existing.salary_max = detail.salary_max
            existing.salary_period = detail.salary_period
            existing.content_hash = content_hash
            existing.status = "expired" if detail.expired else "enriched"
            self.session.flush()
            return existing, False
        job = JobORM(
            provider=provider,
            external_job_id=detail.external_job_id,
            canonical_url=canonical_url,
            title=detail.title,
            company_name=detail.company_name,
            location=detail.location,
            work_mode=detail.work_mode,
            employment_type=detail.employment_type,
            salary_min=detail.salary_min,
            salary_max=detail.salary_max,
            salary_period=detail.salary_period,
            description_raw=detail.description,
            description_normalized=normalized,
            requirements_json=detail.requirements,
            benefits_json=detail.benefits,
            status="expired" if detail.expired else "enriched",
            content_hash=content_hash,
            metadata_json=detail.metadata,
        )
        return self.jobs.save(job), True

    def import_text(
        self, title: str, company_name: str, description: str, source_id: str | None = None
    ) -> tuple[JobORM, bool]:
        """手动粘贴 JD。"""
        external_id = source_id or hashlib.sha256(description.encode("utf-8")).hexdigest()[:20]
        detail = RawJobDetail(
            external_job_id=external_id,
            canonical_url=f"manual://{external_id}",
            title=title,
            company_name=company_name,
            description=description,
            requirements=extract_requirements(description),
            work_mode=detect_work_mode(description),
            employment_type=detect_employment_type(description),
        )
        return self.import_detail("manual", detail)


def normalize_description(text: str) -> str:
    """清理职位描述中的多余空白。"""
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_requirements(text: str) -> list[str]:
    """提取常见技术和要求关键词。"""
    candidates = [
        "Vue",
        "Vue 3",
        "C#",
        ".NET",
        "Python",
        "FastAPI",
        "SQL",
        "Docker",
        "系统设计",
        "软件架构",
        "远程",
        "兼职",
    ]
    lower = text.lower()
    return [item for item in candidates if item.lower() in lower]


def detect_work_mode(text: str) -> str:
    """识别工作方式。"""
    if "远程" in text:
        return "remote"
    if "混合" in text or "部分远程" in text:
        return "hybrid"
    if "现场" in text or "坐班" in text or "驻场" in text:
        return "onsite"
    return "unknown"


def detect_employment_type(text: str) -> str:
    """识别职位合作类型。"""
    mapping = (
        ("兼职", "part_time"),
        ("外包", "contract"),
        ("自由职业", "freelance"),
        ("实习", "internship"),
        ("全职", "full_time"),
    )
    for marker, value in mapping:
        if marker in text:
            return value
    return "unknown"


def canonicalize_url(url: str) -> str:
    """移除常见追踪参数并规范 URL。"""
    if url.startswith("manual://"):
        return url
    split = urlsplit(url)
    allowed = [
        (key, value)
        for key, value in parse_qsl(split.query)
        if not key.lower().startswith(("utm_", "spm", "from"))
    ]
    return urlunsplit(
        (split.scheme.lower(), split.netloc.lower(), split.path.rstrip("/"), urlencode(allowed), "")
    )
