from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "jobos 0.1.0" in result.stdout


def test_cli_doctor_detects_specification() -> None:
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "Architecture specification" in result.stdout
    assert "OK" in result.stdout
