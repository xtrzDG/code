"""
Where the provider contracts live: `tests/contracts/<client package>/fixtures/`
holds what each provider sends (or answers) and `tests/contracts/specs/`
the vendored specifications (tests/contracts/README.md).
"""

import json
from pathlib import Path
from typing import Any

CONTRACTS_DIRECTORY: Path = Path(__file__).resolve().parent
SPECS_DIRECTORY: Path = CONTRACTS_DIRECTORY / "specs"
FIXTURES_FOLDER: str = "fixtures"


def fixtures_directory(provider: str) -> Path:
    """`tests/contracts/<provider>/fixtures` (provider = client package name)."""

    return CONTRACTS_DIRECTORY / provider / FIXTURES_FOLDER


def fixture_path(provider: str, name: str) -> Path:
    path: Path = fixtures_directory(provider) / name
    if not path.is_file():
        raise FileNotFoundError(f"No contract fixture {provider}/{name}.")

    return path


def load_json_fixture(provider: str, name: str) -> Any:
    return json.loads(fixture_path(provider, name).read_text(encoding="utf-8"))


def read_fixture_bytes(provider: str, name: str) -> bytes:
    return fixture_path(provider, name).read_bytes()


def fixture_names(provider: str, suffix: str = ".json") -> list[str]:
    return sorted(
        path.name
        for path in fixtures_directory(provider).iterdir()
        if path.is_file() and path.name.endswith(suffix)
    )
