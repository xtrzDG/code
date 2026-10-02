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
        "TRUSTED_PROXY_HOPS",
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
    assembler = "".join(
        module_path.read_text(encoding="utf-8")
        for module_path in sorted(
            (ROOT / "app" / "utilities" / "config_helpers" / "app_settings").glob(
                "*.py"
            )
        )
    )

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


@pytest.mark.parametrize("relative_path", ["render.yaml", "docker-compose.yml"])
def test_the_api_trusts_only_known_proxies_for_client_addresses(
    relative_path: str,
) -> None:
    # With "*" uvicorn takes the left-most X-Forwarded-For entry, which the
    # client sends itself: audit-log addresses could be forged.
    settings = read(relative_path)

    assert "FORWARDED_ALLOW_IPS" in settings
    assert not re.search(r"FORWARDED_ALLOW_IPS\W+(value: )?\"\*\"", settings)


def test_compose_runs_migrations_before_the_api_and_the_worker() -> None:
    compose = read("docker-compose.yml")

    assert compose.count("condition: service_completed_successfully") == 2
    assert 'command: ["migrate"]' in compose
    assert "BACKEND_URL: http://api:8000" in compose
    assert 'COOKIE_SECURE: "false"' in compose
    assert "./docker/postgres/init:/docker-entrypoint-initdb.d:ro" in compose


def test_copying_env_example_keeps_the_compose_defaults() -> None:
    # Both guides say `cp .env.example .env`, and Compose interpolates
    # ${NAME:-default} from that .env: a non-empty value there replaces the
    # local default docker-compose.yml chose.
    example = dict(
        re.findall(r"^([A-Z0-9_]+)=(.*)$", read(".env.example"), re.MULTILINE)
    )
    compose = read("docker-compose.yml")

    overridden = {
        name: (default, example[name])
        for name, default in re.findall(r"\$\{([A-Z0-9_]+):-([^}$]*)", compose)
        if example.get(name) and example[name] != default
    }

    assert overridden == {}
    # Every local sign-in shares the cabinet container's address, so the
    # per-address cap of login codes is set outright, not interpolated.
    assert 'OTP_SENDS_PER_IP_PER_HOUR: "100"' in compose


def test_the_cabinet_reaches_the_api_only_by_its_internal_address() -> None:
    # Through the public address the API sees Render's egress IP for every
    # owner: one OTP per-address cap for all sign-ins, no client IP in audit.
    blueprint = read("render.yaml")
    cabinet = blueprint.split("name: workshop-cabinet", 1)[1]
    comment = cabinet.split("- key: BACKEND_URL", 1)[0].rsplit("envVars:", 1)[1]
    assert "http://workshop-api:8000" in comment
    assert "Never the public https" in comment
    assert "подойдёт и публичный адрес API" not in read("docs/LAUNCH.md")
    assert "или публичный)" not in read("README.md")
