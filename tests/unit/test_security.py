"""隐私脱敏测试。"""

from jobos.core.security import redact_mapping, redact_text


def test_redact_personal_data_and_secret() -> None:
    text = redact_text("电话 13812345678，邮箱 user@example.com")
    assert "13812345678" not in text
    assert "user@example.com" not in text
    result = redact_mapping({"api_key": "abc", "nested": {"cookie": "x"}})
    assert result["api_key"] != "abc"
