"""跨平台 Chrome 可执行文件检测。"""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path


def detect_chrome_path(configured: Path | None = None) -> Path | None:
    """查找 Chrome 或 Chromium；找不到时返回空。"""
    if configured and configured.exists():
        return configured
    if env_path := os.getenv("CHROME_PATH"):
        path = Path(env_path)
        if path.exists():
            return path
    system = platform.system()
    candidates: list[Path] = []
    if system == "Windows":
        for base in (
            os.getenv("PROGRAMFILES"),
            os.getenv("PROGRAMFILES(X86)"),
            os.getenv("LOCALAPPDATA"),
        ):
            if base:
                candidates.append(Path(base) / "Google/Chrome/Application/chrome.exe")
    elif system == "Darwin":
        candidates.extend(
            [
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
            ]
        )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None
