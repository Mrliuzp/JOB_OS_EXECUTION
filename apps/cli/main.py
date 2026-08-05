"""JobOS-CN Typer 命令行入口。"""

from __future__ import annotations

import asyncio
import platform
import shutil
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import func, select

from apps.api.dependencies import (
    get_engine,
    get_provider_registry,
    get_session_factory,
    get_settings,
)
from jobos import __version__
from jobos.core.config import load_settings
from jobos.core.enums import AutomationLevel
from jobos.domain.schemas import CandidateProfileInput, JobSearchQuery
from jobos.infrastructure.db import init_database
from jobos.infrastructure.db.models import (
    ApplicationORM,
    ApprovalRequestORM,
    JobORM,
    PlatformAccountORM,
)
from jobos.memory.local_store import LocalMemoryStore
from jobos.memory.retrieval import build_evidence_pack
from jobos.rules.engine import RuleEngine
from jobos.services.application_service import ApplicationService
from jobos.services.communication_service import CommunicationService
from jobos.services.discovery_service import DiscoveryService
from jobos.services.job_service import JobService
from jobos.services.profile_service import ProfileService
from jobos.services.scoring_service import ScoringService

app = typer.Typer(name="jobos", help="JobOS-CN 本地优先 AI 求职操作系统。", no_args_is_help=True)
provider_app = typer.Typer(help="管理招聘平台 Provider。")
job_app = typer.Typer(help="管理职位。")
application_app = typer.Typer(help="管理职位申请。")
approvals_app = typer.Typer(help="管理人工审批。")
app.add_typer(provider_app, name="provider")
app.add_typer(job_app, name="job")
app.add_typer(application_app, name="application")
app.add_typer(approvals_app, name="approvals")
console = Console()
ROOT = Path(__file__).resolve().parents[2]


def _version(value: bool) -> None:
    if value:
        typer.echo(f"jobos {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool, typer.Option("--version", "-V", callback=_version, is_eager=True, help="显示版本。")
    ] = False,
) -> None:
    """运行 JobOS-CN 命令。"""
    del version


@app.command()
def init() -> None:
    """初始化配置、数据目录和数据库。"""
    settings = load_settings()
    data_dir = settings.resolved_data_dir()
    for name in ("artifacts", "logs", "browser-profiles", "debug-snapshots"):
        (data_dir / name).mkdir(parents=True, exist_ok=True)
    init_database(get_engine())
    with get_session_factory()() as session, session.begin():
        if ProfileService(session).profiles.first() is None:
            ProfileService(session).upsert_profile(
                CandidateProfileInput(name="请在 Dashboard 中完善姓名")
            )
    console.print(f"[green]初始化完成：{data_dir}[/green]")


@app.command()
def doctor() -> None:
    """检查配置、数据库、Chrome、LLM 和 Provider。"""
    checks: list[tuple[str, bool, str]] = []
    try:
        settings = load_settings()
        checks.append(("配置", True, str(settings.app.data_dir)))
    except Exception as exc:  # 配置诊断必须保留原始错误给用户
        checks.append(("配置", False, str(exc)))
        settings = None
    checks.append(("Python", sys.version_info >= (3, 11), platform.python_version()))
    checks.append(("规格文件", (ROOT / "docs/AI_JOB_OS_EXECUTION_SPEC.md").is_file(), "docs/AI_JOB_OS_EXECUTION_SPEC.md"))
    try:
        init_database(get_engine())
        checks.append(("数据库", True, "连接成功"))
    except Exception as exc:  # 数据库驱动错误需要展示
        checks.append(("数据库", False, str(exc)))
    chrome = None
    if settings and settings.browser.executable_path:
        chrome = str(settings.browser.executable_path)
    else:
        chrome = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("chromium")
    checks.append(("Chrome", bool(chrome), chrome or "未配置；浏览器任务不可用"))
    llm_ok = bool(settings and settings.llm.providers)
    checks.append(("LLM", llm_ok, "已配置" if llm_ok else "未配置；语义任务不可用"))
    checks.append(("Provider", len(get_provider_registry().list()) > 0, ", ".join(item.name for item in get_provider_registry().list())))
    table = Table(title="JobOS-CN 环境诊断")
    table.add_column("检查项")
    table.add_column("状态")
    table.add_column("详情")
    for name, ok, detail in checks:
        table.add_row(name, "通过" if ok else "未通过", detail)
    console.print(table)
    if not all(ok for name, ok, _detail in checks if name not in {"Chrome", "LLM"}):
        raise typer.Exit(code=1)


@app.command()
def api(host: str = "127.0.0.1", port: int = 8000) -> None:
    """启动本地 API。"""
    import uvicorn

    uvicorn.run("apps.api.main:app", host=host, port=port, reload=False)


@app.command()
def worker(once: bool = typer.Option(False, help="只轮询一次。")) -> None:
    """启动任务 Worker。"""
    from apps.worker.main import build_scheduler

    scheduler = build_scheduler()
    if once:
        scheduler.run_once()
    else:
        scheduler.run_forever()


@provider_app.command("list")
def provider_list() -> None:
    """列出 Provider。"""
    for item in get_provider_registry().list():
        console.print(f"{item.name}: {item.capabilities}")


@provider_app.command("add")
def provider_add(provider: str, name: str = "primary") -> None:
    """新增平台账号记录。"""
    get_provider_registry().get(provider)
    with get_session_factory()() as session, session.begin():
        account = PlatformAccountORM(provider=provider, display_name=name)
        session.add(account)
        session.flush()
        console.print(f"已创建平台账号：{account.id}")


@provider_app.command("login")
def provider_login(provider: str) -> None:
    """提示用户在独立 Chrome Profile 中手动登录。"""
    console.print(f"请运行 Dashboard 的 Provider 登录功能，手动完成 {provider} 登录；系统不会保存密码或绕过验证码。")


@provider_app.command("check")
def provider_check(provider: str) -> None:
    """显示平台账号记录状态。"""
    with get_session_factory()() as session:
        account = session.scalar(select(PlatformAccountORM).where(PlatformAccountORM.provider == provider))
        console.print(account.status if account else "尚未创建平台账号")


@app.command()
def discover(
    provider: str = typer.Option("mock", help="Provider 名称。"),
    keyword: list[str] = typer.Option([], "--keyword", "-k", help="可重复填写的关键词。"),
) -> None:
    """发现并补全职位。"""
    async def execute() -> tuple[int, int]:
        with get_session_factory()() as session, session.begin():
            account = session.scalar(
                select(PlatformAccountORM).where(PlatformAccountORM.provider == provider)
            )
            if account is None:
                account = PlatformAccountORM(
                    provider=provider, display_name="primary", status="logged_in" if provider == "mock" else "unknown"
                )
                session.add(account)
                session.flush()
            return await DiscoveryService(session).discover(
                get_provider_registry().get(provider),
                account,
                JobSearchQuery(keywords=keyword or ["Python", "Vue", "C#"]),
            )

    discovered, created = asyncio.run(execute())
    console.print(f"发现 {discovered} 个职位，新建 {created} 个职位。")


@app.command("sync-messages")
def sync_messages(provider: str = typer.Option("mock", help="Provider 名称。")) -> None:
    """同步平台会话和消息。"""
    async def execute() -> tuple[int, int]:
        with get_session_factory()() as session, session.begin():
            account = session.scalar(
                select(PlatformAccountORM).where(PlatformAccountORM.provider == provider)
            )
            if account is None:
                raise typer.BadParameter(f"尚未创建 {provider} 平台账号")
            settings = get_settings()
            return await CommunicationService(
                session, RuleEngine(settings.policies.model_dump())
            ).sync(get_provider_registry().get(provider), account)

    conversations_count, messages_count = asyncio.run(execute())
    console.print(f"新增会话 {conversations_count}，新增消息 {messages_count}。")


@job_app.command("import-text")
def job_import_text(path: Path, title: str, company: str) -> None:
    """从 UTF-8 文本文件导入 JD。"""
    with get_session_factory()() as session, session.begin():
        job, created = JobService(session).import_text(title, company, path.read_text(encoding="utf-8"))
        console.print(f"职位 {job.id}，{'新建' if created else '已更新'}")


@job_app.command("score")
def job_score(job_id: str) -> None:
    """使用规则和事实证据评分。"""
    async def execute() -> float:
        with get_session_factory()() as session, session.begin():
            job = session.get(JobORM, job_id)
            profile = ProfileService(session).get_profile()
            if job is None:
                raise typer.BadParameter("职位不存在")
            evidence = build_evidence_pack(
                LocalMemoryStore(session),
                profile.id,
                job.id,
                job.description_normalized,
                [str(item) for item in job.requirements_json],
            )
            score = await ScoringService(
                session, RuleEngine(get_settings().policies.model_dump())
            ).score(job, profile.id, evidence)
            return score.total_score

    console.print(f"匹配分：{asyncio.run(execute())}")


@application_app.command("create")
def application_create(job_id: str, profile_id: str, level: AutomationLevel = AutomationLevel.L1) -> None:
    """创建职位申请。"""
    with get_session_factory()() as session, session.begin():
        item = ApplicationService(session).create(job_id, profile_id, None, level)
        console.print(item.id)


@application_app.command("prepare")
def application_prepare(application_id: str, resume_id: str, message: str) -> None:
    """准备简历和开场语并创建审批。"""
    with get_session_factory()() as session, session.begin():
        approval = ApplicationService(session).prepare_materials(
            application_id, resume_id, message
        )
        console.print(approval.id if approval else "已按策略自动批准")


@application_app.command("submit")
def application_submit(application_id: str, live: bool = typer.Option(False, help="显式启用真实动作。")) -> None:
    """提交申请；默认 Dry Run。"""
    async def execute() -> str:
        with get_session_factory()() as session, session.begin():
            application = session.get(ApplicationORM, application_id)
            if application is None:
                raise typer.BadParameter("申请不存在")
            job = session.get(JobORM, application.job_id)
            account = session.get(PlatformAccountORM, application.platform_account_id) if application.platform_account_id else None
            if job is None or account is None:
                raise typer.BadParameter("申请缺少职位或平台账号")
            result = await ApplicationService(session).submit(
                application.id,
                get_provider_registry().get(account.provider),
                account,
                job,
                dry_run=not live,
            )
            return result.detail

    console.print(asyncio.run(execute()))


@application_app.command("mark-submitted")
def application_mark_submitted(application_id: str, external_id: str | None = None) -> None:
    """手动标记平台申请完成。"""
    with get_session_factory()() as session, session.begin():
        item = ApplicationService(session).mark_submitted(application_id, external_id)
        console.print(item.status)


@approvals_app.command("list")
def approvals_list() -> None:
    """列出待审批项。"""
    with get_session_factory()() as session:
        items = session.scalars(select(ApprovalRequestORM).where(ApprovalRequestORM.status == "pending")).all()
        for item in items:
            console.print(f"{item.id} {item.approval_type} {item.reason}")


@approvals_app.command("approve")
def approvals_approve(approval_id: str) -> None:
    """批准申请类审批。"""
    with get_session_factory()() as session, session.begin():
        item = ApplicationService(session).resolve_approval(approval_id, True)
        console.print(item.status)


@approvals_app.command("reject")
def approvals_reject(approval_id: str) -> None:
    """拒绝申请类审批。"""
    with get_session_factory()() as session, session.begin():
        item = ApplicationService(session).resolve_approval(approval_id, False)
        console.print(item.status)


@app.command()
def status() -> None:
    """显示职位、申请和审批数量。"""
    with get_session_factory()() as session:
        counts = {
            "职位": int(session.scalar(select(func.count(JobORM.id))) or 0),
            "申请": int(session.scalar(select(func.count(ApplicationORM.id))) or 0),
            "待审批": int(session.scalar(select(func.count(ApprovalRequestORM.id)).where(ApprovalRequestORM.status == "pending")) or 0),
        }
    for key, value in counts.items():
        console.print(f"{key}: {value}")


@app.command()
def dashboard() -> None:
    """显示 Dashboard 启动说明。"""
    console.print("请分别运行 `jobos api` 与 `cd apps/web; npm run dev`。")


@app.command()
def run(dry_run: bool = typer.Option(True, "--dry-run/--live", help="默认只执行 Dry Run。")) -> None:
    """执行一次安全工作流入口。"""
    mode = "Dry Run" if dry_run else "真实动作模式"
    console.print(f"当前模式：{mode}。发现、评分和材料任务由 Worker 队列执行。")


if __name__ == "__main__":
    app()
