"""辅助组件覆盖测试。"""

from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

from apps.worker.scheduler import WorkerScheduler
from jobos.browser.action_executor import BrowserActionExecutor
from jobos.browser.models import BrowserAction, ExpectedState, SelectorSpec
from jobos.browser.page_snapshot import PageSnapshotStore
from jobos.browser.selectors import load_selector_registry
from jobos.core.errors import NotFoundError, ProviderActionRejected
from jobos.infrastructure.db.models import CandidateProfileORM
from jobos.llm.schemas import LLMResponse
from jobos.llm.usage import summarize_usage
from jobos.memory.codex_memory_adapter import CodexMemoryAdapter
from jobos.providers.mock import MockProvider
from jobos.providers.registry import ProviderRegistry
from jobos.workflow.orchestrator import WorkflowOrchestrator
from jobos.workflow.task_queue import TaskQueue


class FakeLocator:
    """浏览器定位器替身。"""

    def __init__(self) -> None:
        self.value = "提取文本"

    async def click(self, timeout: float | None = None) -> None:
        del timeout

    async def fill(self, value: str, timeout: float | None = None) -> None:
        del timeout
        self.value = value

    async def select_option(self, value: str) -> Any:
        self.value = value
        return None

    async def set_input_files(self, files: str) -> None:
        self.value = files

    async def inner_text(self) -> str:
        return self.value


class FakePage:
    """浏览器页面替身。"""

    url = "https://example.test/jobs"

    def __init__(self) -> None:
        self.html = "<html><body>提交成功</body></html>"
        self.item = FakeLocator()

    async def goto(self, url: str, timeout: float | None = None) -> None:
        del timeout
        self.url = url

    async def wait_for_timeout(self, timeout: float) -> None:
        del timeout

    async def content(self) -> str:
        return self.html

    def locator(self, selector: str) -> FakeLocator:
        del selector
        return self.item

    def get_by_text(self, text: str, exact: bool = False) -> FakeLocator:
        del text, exact
        return self.item

    def get_by_label(self, text: str) -> FakeLocator:
        del text
        return self.item

    def get_by_role(self, role: str, name: str | None = None) -> FakeLocator:
        del role, name
        return self.item


@pytest.mark.asyncio
async def test_action_executor_and_snapshot(tmp_path: Path) -> None:
    page = FakePage()
    executor = BrowserActionExecutor()
    await executor.execute(
        page,
        BrowserAction(
            action_type="click",
            selector=SelectorSpec(kind="css", value="#submit"),
            expected_state=ExpectedState(text_present="提交成功", url_contains="jobs"),
        ),
    )
    extracted = await executor.execute(
        page, BrowserAction(action_type="extract", selector=SelectorSpec(kind="text", value="文本"))
    )
    assert extracted == "提取文本"
    with pytest.raises(ProviderActionRejected):
        await executor.execute(page, BrowserAction(action_type="click"))
    snapshot = PageSnapshotStore(tmp_path).save(
        "trace", "电话 13812345678", {"api_key": "secret"}, {"role": "main"}
    )
    assert "13812345678" not in (snapshot / "page.html").read_text(encoding="utf-8")


def test_selector_usage_registry_and_codex_adapter(tmp_path: Path, session: Session) -> None:
    path = tmp_path / "selector.yaml"
    path.write_text("key: test\nstrategies: []", encoding="utf-8")
    assert load_selector_registry(path)["key"] == "test"
    summary = summarize_usage(
        [LLMResponse(content="", model="m", provider="p", prompt_tokens=3, completion_tokens=2)]
    )
    assert summary.prompt_tokens == 3
    profile = CandidateProfileORM(name="测试用户")
    session.add(profile)
    session.flush()
    count = CodexMemoryAdapter(session).sync(
        profile.id, [{"id": "external-1", "fact_type": "project", "statement": "真实项目"}]
    )
    assert count == 1


def test_registry_and_orchestrator(factory: sessionmaker[Session]) -> None:
    registry = ProviderRegistry()
    registry.register(MockProvider())
    assert registry.get("mock").name == "mock"
    assert len(registry.list()) == 1
    with pytest.raises(NotFoundError):
        registry.get("missing")

    queue = TaskQueue(factory)
    queue.enqueue("TEST", "entity", "1", "test:1", {"value": 2})
    orchestrator = WorkflowOrchestrator(
        queue, {"TEST": lambda payload: {"result": int(payload["value"]) * 2}}
    )
    scheduler = WorkerScheduler(orchestrator, "worker", poll_interval_seconds=0)
    assert scheduler.run_once() is True
    assert scheduler.run_once() is False
