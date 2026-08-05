from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_example_configuration_files_exist() -> None:
    expected = {
        ROOT / "config" / "app.example.yaml",
        ROOT / "config" / "policies.example.yaml",
        ROOT / "config" / "providers.example.yaml",
        ROOT / "config" / "prompts.example.yaml",
    }

    assert all(path.is_file() for path in expected)


def test_architecture_specification_exists() -> None:
    assert (ROOT / "docs" / "AI_JOB_OS_EXECUTION_SPEC.md").is_file()
