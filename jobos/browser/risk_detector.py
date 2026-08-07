"""验证码和平台风控检测。"""

from dataclasses import dataclass

_RISK_MARKERS = (
    "验证码",
    "滑块",
    "安全验证",
    "访问过于频繁",
    "异常请求",
    "账号风险",
    "请重新登录",
    "扫码登录",
    "captcha",
)


@dataclass(frozen=True)
class BrowserRisk:
    """页面风险检测结果。"""

    detected: bool
    marker: str | None = None


def detect_browser_risk(text: str) -> BrowserRisk:
    """检测页面文本是否包含验证码或风控标识。"""
    lower = text.lower()
    for marker in _RISK_MARKERS:
        if marker.lower() in lower:
            return BrowserRisk(detected=True, marker=marker)
    return BrowserRisk(detected=False)
