"""The Docker, Compose, Render and CI files point at things that exist."""

import importlib
import importlib.util
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.adapters.storage.postgres.migrate import DEFAULT_MIGRATIONS_DIRECTORY
from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
)

ROOT: Path = Path(__file__).resolve().parents[2]
ENTRYPOINT: Path = ROOT / "docker" / "entrypoint.sh"
POSTGRES_INIT: Path = ROOT / "docker" / "postgres" / "init" / "01-create-app-role.sh"
# Read by SDKs or by the platforms, not by the settings assembler.
EXTERNAL_VARIABLES: frozenset[str] = frozenset(
    {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "PORT",
        "FORWARDED_ALLOW_IPS",
        "BACKEND_URL",
        "COOKIE_SECURE",
    }
)


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def env_example_variables() -> set[str]:
    return set(re.findall(r"^([A-Z0-9_]+)=", read(".env.example"), re.MULTILINE))


def test_entrypoint_roles_run_existing_modules() -> None:
    script = ENTRYPOINT.read_text(encoding="utf-8")

    for module_name in re.findall(r"python -m ([\w.]+)", script):
        assert importlib.util.find_spec(module_name) is not None, module_name

    factory = re.search(r"uvicorn ([\w.]+):(\w+) --factory", script)
    assert factory is not None
    assert callable(
        getattr(importlib.import_module(factory.group(1)), factory.group(2))
    )
    assert "--proxy-headers" in script
    assert ENTRYPOINT.stat().st_mode & 0o111
    assert POSTGRES_INIT.stat().st_mode & 0o111


@pytest.mark.skipif(shutil.which("sh") is None, reason="no POSIX shell")
@pytest.mark.parametrize("script", [ENTRYPOINT, POSTGRES_INIT])
def test_shell_scripts_parse(script: Path) -> None:
    result = subprocess.run(
        ["sh", "-n", str(script)], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr


def test_dockerfile_copies_what_the_image_needs() -> None:
    dockerfile = read("Dockerfile")
    copied = re.findall(r"^COPY (?!--from)(\S+)", dockerfile, re.MULTILINE)

    assert copied == ["app", "migrations", "docs/legal", "docker/entrypoint.sh"]
    for source in copied:
        assert (ROOT / source).exists(), source

    assert DEFAULT_MIGRATIONS_DIRECTORY == ROOT / "migrations"
    assert DEFAULT_LEGAL_DOCUMENTS_DIRECTORY == ROOT / "docs" / "legal"
    assert "uv sync --frozen --no-dev" in dockerfile
    assert "/healthz" in dockerfile
    assert re.search(r"^USER \d+:\d+$", dockerfile, re.MULTILINE)
    ignored = read(".dockerignore").splitlines()
    assert not {
        "app",
        "migrations",
        "docs/legal",
        "docker",
        "uv.lock",
        "pyproject.toml",
    } & set(ignored)
    assert "!docs/legal" in ignored


def test_every_documented_variable_is_read() -> None:
    assembler = read("app/utilities/config_helpers/app_settings_assembler.py")

    unread = {
        variable
        for variable in env_example_variables()
        if f'"{variable}"' not in assembler and variable not in EXTERNAL_VARIABLES
    }

    assert unread == set()


def test_render_blueprint_uses_known_variables_and_the_eu_region() -> None:
    blueprint = read("render.yaml")
    variables = set(re.findall(r"- key: ([A-Z0-9_]+)", blueprint))

    assert variables - env_example_variables() - EXTERNAL_VARIABLES == set()
    assert set(re.findall(r"region: (\w+)", blueprint)) == {"frankfurt"}
    assert "preDeployCommand: workshop migrate" in blueprint
    assert "healthCheckPath: /healthz" in blueprint
    assert "dockerfilePath: ./web/Dockerfile" in blueprint


def test_compose_runs_migrations_before_the_api_and_the_worker() -> None:
    compose = read("docker-compose.yml")

    assert compose.count("condition: service_completed_successfully") == 2
    assert 'command: ["migrate"]' in compose
    assert "BACKEND_URL: http://api:8000" in compose
    assert 'COOKIE_SECURE: "false"' in compose
    assert "./docker/postgres/init:/docker-entrypoint-initdb.d:ro" in compose
