"""JobOS 软件包测试。"""

import jobos


def test_jobos_package_version() -> None:
    """软件包应公开当前版本。"""
    assert jobos.__version__ == "0.2.0"
