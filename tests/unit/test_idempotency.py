"""幂等键测试。"""

from jobos.core.idempotency import build_idempotency_key


def test_idempotency_key_is_stable() -> None:
    assert build_idempotency_key("x", {"a": 1, "b": 2}) == build_idempotency_key(
        "x", {"b": 2, "a": 1}
    )
