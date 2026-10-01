"""
Every environment variable is documented where people look for it, every
documented one is read by something, and the deployment files set what a
working installation needs.

Sources of truth:

- the settings assembler (`app_settings_assembler.py`) and the provider SDKs
  for the backend; `.env.example` and the "Окружение" table of `README.md`
  for people;
- `web/src` (the cabinet's server code) for the cabinet; `web/.env.example`
  and the "Environment" table of `web/README.md` for people;
- `docker-compose.yml` and `render.yaml` for the deployments.
"""

import ast
import inspect
import re
from collections.abc import Iterator, Mapping
from pathlib import Path

import anthropic
import openai
import pytest

from app.adapters.security.secret_cipher_adapter import MIN_DERIVED_SECRET_LENGTH
from app.clients.anthropic import anthropic_messages_client
from app.clients.openai import openai_responses_client
from app.utilities.config_helpers.app_settings_assembler import (
    DEFAULT_OPENAI_BASE_URL,
    assemble_app_settings,
)

ROOT: Path = Path(__file__).resolve().parents[2]
ASSEMBLER: Path = (
    ROOT / "app" / "utilities" / "config_helpers" / "app_settings_assembler.py"
)
VARIABLE_NAME: re.Pattern[str] = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+")

# Read by the provider SDKs themselves: the clients never pass the key, so
# the SDK takes it from the environment. Set like any other variable.
SDK_VARIABLES: frozenset[str] = frozenset({"OPENAI_API_KEY", "ANTHROPIC_API_KEY"})

# Deployment-only: read when the image starts (docker/entrypoint.sh runs
# uvicorn), not by the application. The Dockerfile, docker-compose.yml and
# render.yaml set them, so README.md describes them and .env.example does
# not list them.
DEPLOYMENT_VARIABLES: frozenset[str] = frozenset(
    {
        # uvicorn --port; the Dockerfile sets 8000, Render sets it too.
        "PORT",
        # uvicorn --proxy-headers: address ranges of the trusted proxies.
        "FORWARDED_ALLOW_IPS",
    }
)

# Docker Compose interpolation only (docker-compose.yml), for a local run:
# published ports and the local database roles.
COMPOSE_VARIABLES: frozenset[str] = frozenset(
    {
        "API_PORT",
        "WEB_PORT",
        "POSTGRES_PASSWORD",
        "WORKSHOP_DB_USER",
        "WORKSHOP_DB_PASSWORD",
        "WORKSHOP_DB_NAME",
    }
)

# Set by Next.js itself (`next build`, `next start`), never by people.
NEXT_JS_VARIABLES: frozenset[str] = frozenset({"NODE_ENV"})

# What every deployment of the backend (API and worker) sets: without them
# production refuses to start, keeps no data, cannot be reached by webhooks
# or cannot send owners back to the cabinet.
REQUIRED_BACKEND_VARIABLES: frozenset[str] = frozenset(
    {
        "APP_ENV",
        "APP_BASE_URL",
        "CABINET_BASE_URL",
        "CORS_ALLOWED_ORIGINS",
        "DATABASE_URL",
        "ENCRYPTION_KEY",
        "FORWARDED_ALLOW_IPS",
    }
)
REQUIRED_CABINET_VARIABLES: frozenset[str] = frozenset({"BACKEND_URL", "COOKIE_SECURE"})

# .env.example variables without a default value that the Render API may
# leave out; the Blueprint asks for every other one when it is created.
RENDER_OPTIONAL_VARIABLES: frozenset[str] = frozenset(
    {
        # The default follows LLM_PROVIDER (gpt-5-mini, claude-opus-5-5).
        "LLM_MODEL_ID",
        "LLM_JUDGE_MODEL_ID",
        # Development and tests only; refused in production.
        "OTP_LOG_CODES",
    }
)

# The assembler reads some variables only in some environments: each
# scenario is assembled once and every name it asks for is recorded.
ASSEMBLY_SCENARIOS: tuple[dict[str, str], ...] = (
    {},
    {
        "APP_ENV": "production",
        "ELEVENLABS_API_BASE_URL": "https://api.elevenlabs.io",
        "ELEVENLABS_ALLOW_NON_EU_REGION": "true",
    },
)


class RecordingEnvironment(Mapping[str, str]):
    """An environment that remembers which variables were asked for."""

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values: dict[str, str] = dict(values)
        self.read_names: set[str] = set()

    def __getitem__(self, key: str) -> str:
        # Mapping.get and `in` ask here too.
        self.read_names.add(key)
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        raise AssertionError("The settings assembler must read variables by name.")

    def __len__(self) -> int:
        return len(self._values)


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def assembler_variables() -> set[str]:
    """Every variable name written in the settings assembler."""

    tree = ast.parse(ASSEMBLER.read_text(encoding="utf-8"))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and VARIABLE_NAME.fullmatch(node.value) is not None
    }


def backend_variables() -> set[str]:
    """What the backend reads: the assembler and the SDKs."""

    return assembler_variables() | SDK_VARIABLES


def env_file_values(relative_path: str, include_commented: bool) -> dict[str, str]:
    """`NAME=value` lines of an env file (and `# NAME=value` when asked)."""

    prefix: str = r"^(?:#\s*)?" if include_commented else r"^"
    pattern: str = prefix + r"([A-Z][A-Z0-9_]*)=(.*)$"
    return dict(re.findall(pattern, read(relative_path), re.MULTILINE))


def table_variables(relative_path: str, heading: str) -> set[str]:
    """Variables named in the first column of the tables under a heading."""

    lines: list[str] = read(relative_path).splitlines()
    level: int = len(heading.split(" ", 1)[0])
    names: set[str] = set()
    is_in_code: bool = False
    for line in lines[lines.index(heading) + 1 :]:
        if line.startswith("```"):
            is_in_code = not is_in_code
        heading_match = re.match(r"(#+) ", line)
        if (
            not is_in_code
            and heading_match is not None
            and len(heading_match.group(1)) <= level
        ):
            break

        cells: list[str] = line.split("|")
        if line.startswith("|") and len(cells) > 2:
            names.update(re.findall(r"`([A-Z][A-Z0-9_]*)`", cells[1]))

    return names


def cabinet_variables() -> set[str]:
    """Variables the cabinet's own code reads (`process.env` passed as `env`)."""

    names: set[str] = set()
    for path in (ROOT / "web" / "src").rglob("*.ts*"):
        if ".test." not in path.name:
            source: str = path.read_text(encoding="utf-8")
            names.update(re.findall(r"\benv\.([A-Z][A-Z0-9_]*)", source))

    return names - NEXT_JS_VARIABLES


def render_services() -> dict[str, set[str]]:
    """Variables of each Render service, those of its groups included."""

    blueprint: str = read("render.yaml")
    groups_text, services_text = blueprint.split("\nservices:\n", 1)
    groups_text = groups_text.split("\nenvVarGroups:\n", 1)[1]
    groups: dict[str, set[str]] = {}
    for chunk in re.split(r"^  - name: ", groups_text, flags=re.MULTILINE)[1:]:
        group_name: str = chunk.split("\n", 1)[0].strip()
        groups[group_name] = set(re.findall(r"- key: ([A-Z0-9_]+)", chunk))

    services: dict[str, set[str]] = {}
    for chunk in re.split(r"^  - type: ", services_text, flags=re.MULTILINE)[1:]:
        name_match = re.search(r"^    name: (\S+)$", chunk, re.MULTILINE)
        assert name_match is not None
        variables: set[str] = set(re.findall(r"- key: ([A-Z0-9_]+)", chunk))
        for group_name in re.findall(r"- fromGroup: (\S+)", chunk):
            variables |= groups[group_name]
        services[name_match.group(1)] = variables

    return services


def compose_environment(block_line: str) -> dict[str, str]:
    """`environment:` of the Compose block that starts with this line."""

    lines: list[str] = read("docker-compose.yml").splitlines()
    start: int = lines.index(block_line)
    block_indentation: int = indentation(block_line)
    environment_indentation: int | None = None
    variables: dict[str, str] = {}
    for line in lines[start + 1 :]:
        if line.strip() == "" or line.lstrip().startswith("#"):
            continue

        line_indentation: int = indentation(line)
        if line_indentation <= block_indentation:
            break

        if environment_indentation is None:
            if line.strip() == "environment:":
                environment_indentation = line_indentation
            continue

        if line_indentation <= environment_indentation:
            break

        name, value = line.strip().split(": ", 1)
        variables[name] = value

    return variables


def compose_default(value: str) -> str:
    """The default of `${NAME:-default}`."""

    match = re.fullmatch(r"\$\{[A-Z][A-Z0-9_]*:-(.+)\}", value)
    assert match is not None, value
    return match.group(1)


def test_the_name_scan_finds_exactly_what_the_assembler_reads() -> None:
    # The other tests scan the assembler's source; assembling real settings
    # proves that the scan misses nothing and lists nothing unread.
    read_names: set[str] = set()
    for scenario in ASSEMBLY_SCENARIOS:
        environment = RecordingEnvironment(scenario)
        assemble_app_settings(environment)
        read_names |= environment.read_names

    assert read_names == assembler_variables()


def test_every_backend_variable_is_in_env_example() -> None:
    documented: set[str] = set(env_file_values(".env.example", False))

    assert backend_variables() - documented == set()


def test_every_env_example_variable_is_read() -> None:
    documented: set[str] = set(env_file_values(".env.example", False))

    unread: set[str] = (
        documented - backend_variables() - DEPLOYMENT_VARIABLES - COMPOSE_VARIABLES
    )

    assert unread == set()


def test_the_readme_environment_table_lists_every_backend_variable() -> None:
    table: set[str] = table_variables("README.md", "## Окружение")
    expected: set[str] = backend_variables() | DEPLOYMENT_VARIABLES

    assert expected - table == set()
    assert table - expected == set()


def test_the_sdks_read_their_keys_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-the-environment")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-the-environment")

    openai_client = openai.OpenAI(base_url=DEFAULT_OPENAI_BASE_URL)
    anthropic_client = anthropic.Anthropic()

    assert openai_client.api_key == "sk-from-the-environment"
    assert anthropic_client.api_key == "sk-ant-from-the-environment"
    for client_module in (openai_responses_client, anthropic_messages_client):
        assert "api_key=" not in inspect.getsource(client_module)


def test_every_cabinet_variable_is_documented() -> None:
    read_names: set[str] = cabinet_variables()

    assert read_names >= REQUIRED_CABINET_VARIABLES
    assert set(env_file_values("web/.env.example", True)) == read_names
    assert table_variables("web/README.md", "### Environment") == read_names


def test_deployment_files_set_only_known_variables() -> None:
    known: set[str] = backend_variables() | DEPLOYMENT_VARIABLES | cabinet_variables()
    compose: str = read("docker-compose.yml")
    compose_variables: set[str] = set(compose_environment("x-backend: &backend"))
    compose_variables |= set(compose_environment("  web:"))
    interpolated: set[str] = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", compose))

    for service, variables in render_services().items():
        assert variables - known == set(), service
    assert compose_variables - known == set()
    assert interpolated - known - COMPOSE_VARIABLES == set()


def test_render_sets_what_a_deployment_needs() -> None:
    services: dict[str, set[str]] = render_services()
    api: set[str] = services["workshop-api"]
    without_default: set[str] = {
        name
        for name, value in env_file_values(".env.example", False).items()
        if value == ""
    }

    assert api >= REQUIRED_BACKEND_VARIABLES | {"PORT"}
    assert without_default - RENDER_OPTIONAL_VARIABLES - api == set()
    # The worker runs the same code with the same settings.
    assert services["workshop-worker"] == api - {"PORT"}
    assert services["workshop-cabinet"] >= REQUIRED_CABINET_VARIABLES | {
        "TRUSTED_PROXY_HOPS"
    }


def test_the_render_worker_copies_the_api_values() -> None:
    worker: str = read("render.yaml").split("    name: workshop-worker\n", 1)[1]
    worker = worker.split("\n  - type: ", 1)[0]

    copies: list[tuple[str, str, str]] = re.findall(
        r"- key: ([A-Z0-9_]+)\n\s+fromService:\n\s+type: web\n\s+name: (\S+)\n"
        r"\s+envVarKey: ([A-Z0-9_]+)",
        worker,
    )

    assert len(copies) == worker.count("fromService:") > 0
    for key, service, source_key in copies:
        assert (service, source_key) == ("workshop-api", key)


def test_compose_sets_what_a_local_run_needs() -> None:
    backend: dict[str, str] = compose_environment("x-backend: &backend")
    web: dict[str, str] = compose_environment("  web:")

    assert set(backend) >= REQUIRED_BACKEND_VARIABLES
    assert set(web) >= REQUIRED_CABINET_VARIABLES
    # API and worker share one key by default, long enough to use as is.
    assert len(compose_default(backend["ENCRYPTION_KEY"])) >= MIN_DERIVED_SECRET_LENGTH
    # The cabinet's address is also its origin; its server reaches the API
    # inside the Compose network.
    assert compose_default(backend["CABINET_BASE_URL"]) == compose_default(
        backend["CORS_ALLOWED_ORIGINS"]
    )
    assert web["BACKEND_URL"] == "http://api:8000"
