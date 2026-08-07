"""Prompt 文件注册表。"""

from pathlib import Path


class PromptRegistry:
    """按任务和版本读取 Prompt，避免在代码中散落长文本。"""

    def __init__(self, root: Path) -> None:
        self.root = root

    def get(self, task: str, version: str = "v1") -> str:
        """读取 Prompt 文本。"""
        path = self.root / task / f"{version}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt 不存在：{path}")
        return path.read_text(encoding="utf-8")
