"""Typer CLI entry point for JobOS-CN."""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from jobos import __version__

app = typer.Typer(name="jobos", help="JobOS-CN local-first job search operating system.")
console = Console()
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DoctorCheck:
    """One deterministic repository bootstrap check."""

    name: str
    ok: bool
    detail: str


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"jobos {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Run JobOS-CN commands."""
    del version


@app.command()
def doctor() -> None:
    """Check the WP-001 local development prerequisites."""
    required_files = [
        REPOSITORY_ROOT / "docs" / "AI_JOB_OS_EXECUTION_SPEC.md",
        REPOSITORY_ROOT / "config" / "app.example.yaml",
        REPOSITORY_ROOT / "config" / "policies.example.yaml",
        REPOSITORY_ROOT / "config" / "providers.example.yaml",
        REPOSITORY_ROOT / "config" / "prompts.example.yaml",
    ]
    checks = [
        DoctorCheck(
            name="Python",
            ok=sys.version_info >= (3, 11),
            detail=platform.python_version(),
        ),
        DoctorCheck(name="Operating system", ok=True, detail=platform.platform()),
        DoctorCheck(name="Working directory", ok=True, detail=str(Path.cwd())),
        DoctorCheck(
            name="Architecture specification",
            ok=required_files[0].is_file(),
            detail=str(required_files[0]),
        ),
        DoctorCheck(
            name="Example configuration",
            ok=all(path.is_file() for path in required_files[1:]),
            detail=f"{sum(path.is_file() for path in required_files[1:])}/4 files",
        ),
    ]

    table = Table(title="JobOS-CN Doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for check in checks:
        table.add_row(check.name, "OK" if check.ok else "FAILED", check.detail)
    console.print(table)

    if not all(check.ok for check in checks):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
