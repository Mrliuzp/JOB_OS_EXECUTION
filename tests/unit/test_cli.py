"""JobOS 命令行测试。"""

from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


def test_cli_version() -> None:
    """版本命令应返回当前软件版本。"""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "jobos 0.2.0" in result.stdout


def test_cli_doctor_detects_specification() -> None:
    """环境诊断应识别项目规格文件。"""
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "规格文件" in result.stdout
    assert "通过" in result.stdout
