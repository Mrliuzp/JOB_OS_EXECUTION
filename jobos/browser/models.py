"""浏览器动作与会话模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class SelectorSpec:
    """可按优先级尝试的元素定位信息。"""

    kind: Literal["role", "text", "css", "label"]
    value: str
    role_name: str | None = None


@dataclass(frozen=True)
class ExpectedState:
    """动作完成后的期望页面状态。"""

    text_present: str | None = None
    url_contains: str | None = None


@dataclass(frozen=True)
class BrowserAction:
    """受控浏览器动作。"""

    action_type: Literal["goto", "click", "fill", "select", "upload", "wait", "snapshot", "extract"]
    selector: SelectorSpec | None = None
    value: str | None = None
    timeout_ms: int = 15000
    expected_state: ExpectedState | None = None


@dataclass
class BrowserSession:
    """独立 Chrome 会话。"""

    session_id: str
    account_id: str
    browser_profile_path: Path
    cdp_port: int
    process_id: int
    started_at: datetime
    last_heartbeat_at: datetime
    purpose: str
