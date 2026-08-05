"""失败页面调试资料保存。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jobos.core.security import redact_mapping, redact_text


class PageSnapshotStore:
    """保存脱敏后的页面和任务上下文。"""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        trace_id: str,
        html: str,
        context: dict[str, Any],
        accessibility: dict[str, Any] | None = None,
    ) -> Path:
        """创建单次调试目录。"""
        directory = self.root / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "page.html").write_text(redact_text(html), encoding="utf-8")
        (directory / "task-context.json").write_text(
            json.dumps(redact_mapping(context), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if accessibility is not None:
            (directory / "accessibility-tree.json").write_text(
                json.dumps(redact_mapping(accessibility), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return directory
