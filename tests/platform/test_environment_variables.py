"""
Every environment variable is documented where people look for it, every
documented one is read by something, and the deployment files set what a
working installation needs.

Sources of truth:

- the settings assembler (`app/utilities/config_helpers/app_settings/`) and
  the provider SDKs for the backend; `.env.example` and the "Окружение"
  table of `README.md` for people;
- `web/src` (the cabinet's server code) for the cabinet; `web/.env.example`
  and the "Environment" table of `web/README.md` for people;
- `docker-compose.yml` and `render.yaml` for the deployments.

The owner's launch guide (`docs/LAUNCH.md`) may name only variables, API
routes and files that exist.
"""

import ast
import inspect
import json
import re
from collections.abc import Iterator, Mapping
from pathlib import Path

import anthropic
import openai
import pytest

from app.adapters.security.secret_cipher_adapter import (
    MIN_DERIVED_SECRET_LENGTH,
    PUBLIC_ENCRYPTION_KEYS,
)
from app.clients.anthropic import anthropic_messages_client
from app.clients.openai import openai_responses_client
from app.utilities.channels.channel_endpoints import (
    WIDGET_DEMO_PATH,
    WIDGET_SCRIPT_PATH,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.config_helpers.app_settings.llm_settings_section import (
    DEFAULT_OPENAI_BASE_URL,
)

ROOT: Path = Path(__file__).resolve().parents[2]
# The assembler and its sections, one module per topic.
ASSEMBLER_DIRECTORY: Path = (
    ROOT / "app" / "utilities" / "config_helpers" / "app_settings"
)
VARIABLE_NAME: re.Pattern[str] = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+")
LAUNCH_GUIDE: str = "docs/LAUNCH.md"
# The API's routes as the cabinet's generated client knows them.
OPENAPI_DESCRIPTION: str = "web/openapi.json"
# Routes outside the OpenAPI description (include_in_schema=False).
UNDESCRIBED_ROUTES: frozenset[str] = frozenset(
    {"/healthz", WIDGET_SCRIPT_PATH, WIDGET_DEMO_PATH}
)
# The guide names the curated country data relative to this folder.
REGISTRIES: Path = ROOT / "app" / "registries"

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

    return {
        node.value
        for module_path in sorted(ASSEMBLER_DIRECTORY.glob("*.py"))
        for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8")))
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
    # API and worker share one key by default, long enough to use as is;
    # production refuses it, since it is printed here.
    assert len(compose_default(backend["ENCRYPTION_KEY"])) >= MIN_DERIVED_SECRET_LENGTH
    assert compose_default(backend["ENCRYPTION_KEY"]) in PUBLIC_ENCRYPTION_KEYS
    # The cabinet's address is also its origin; its server reaches the API
    # inside the Compose network.
    assert compose_default(backend["CABINET_BASE_URL"]) == compose_default(
        backend["CORS_ALLOWED_ORIGINS"]
    )
    # Addresses follow the published ports, so changing API_PORT or WEB_PORT
    # in .env (docs/LAUNCH.md) keeps the widget code, its preview and the
    # cabinet's address reachable.
    assert compose_default(backend["APP_BASE_URL"]) == (
        "http://localhost:${API_PORT:-8000}"
    )
    assert compose_default(backend["CABINET_BASE_URL"]) == (
        "http://localhost:${WEB_PORT:-3000}"
    )
    assert web["BACKEND_URL"] == "http://api:8000"


def test_the_launch_guide_names_only_what_exists() -> None:
    guide: str = read(LAUNCH_GUIDE)
    known: set[str] = (
        backend_variables()
        | DEPLOYMENT_VARIABLES
        | COMPOSE_VARIABLES
        | cabinet_variables()
    )
    described: set[str] = {
        re.sub(r"\{[^}]*\}", "{}", path)
        for path in json.loads(read(OPENAPI_DESCRIPTION))["paths"]
    }
    routes: set[str] = {
        re.sub(r"\{[^}]*\}", "{}", route.split("?", 1)[0])
        for route in re.findall(r"`(/(?:v1/|healthz|widget)[^`\s]*)`", guide)
    }
    files: list[str] = re.findall(r"`([\w/.-]+\.(?:py|md|yml|yaml))`", guide)

    assert set(VARIABLE_NAME.findall(guide)) - known == set()
    assert "/v1/channels/meta/webhook" in routes
    assert routes - described - UNDESCRIBED_ROUTES == set()
    for name in files:
        assert (ROOT / name).exists() or (REGISTRIES / name).exists(), name


README: str = "README.md"
BUSINESS_PREFIX: str = "/v1/businesses/{business_id}"
HTTP_METHODS: frozenset[str] = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})
API_ADDRESS_WITH_EXTRA_SCHEME: re.Pattern[str] = re.compile(
    r"https?://<(?:APP_BASE_URL|адрес API)>"
)
# The old claim that the Render worker takes every value of the API.
COPIES_EVERY_VALUE: re.Pattern[str] = re.compile(
    r"(копирует|берёт) все значения|воркер возьмёт их сам|copies the API's values"
)
# Russian labels of the cabinet the guide names (web/src/i18n, workspace).
WEB_CHAT_CARD: str = "«Чат на сайте»"
TURN_ON: str = "«Включить»"
WIDGET_SECTION_LABELS: tuple[str, ...] = (
    "«Код чата для сайта»",
    "«Открыть живой предпросмотр»",
)


def test_render_docs_send_undeclared_variables_to_the_shared_group() -> None:
    # fromService copies one named key, so a variable render.yaml does not
    # give the worker reaches it only through the shared group.
    services: dict[str, set[str]] = render_services()
    undeclared: set[str] = backend_variables() - services["workshop-worker"]
    assert {"LLM_MODEL_ID", "OPENAI_BASE_URL", "WORKER_POLL_SECONDS"} <= undeclared
    for path in (LAUNCH_GUIDE, README, "render.yaml"):
        text: str = read(path)
        assert "workshop-backend" in text, path
        assert not re.search(COPIES_EVERY_VALUE, text), path


def test_the_guides_do_not_put_a_scheme_before_the_api_address() -> None:
    # APP_BASE_URL (PublicBaseUrl) already starts with https://, and the guides
    # define "адрес API" as that value: "https://<APP_BASE_URL>" would become
    # "https://https://...".
    for path in (README, LAUNCH_GUIDE):
        assert API_ADDRESS_WITH_EXTRA_SCHEME.findall(read(path)) == [], path


def test_the_guide_turns_the_website_chat_on_before_its_code() -> None:
    # The cabinet shows the widget code and its preview only once the
    # website chat is on, and the widget refuses messages until then.
    workspace: str = read("web/src/i18n/messages/sections/workspace.ts")
    for label in (WEB_CHAT_CARD, TURN_ON, *WIDGET_SECTION_LABELS):
        assert f'"{label.strip("«»")}"' in workspace, label

    paragraphs: list[str] = re.split(r"\n\s*\n|\n(?=\d+\. |\| )", read(LAUNCH_GUIDE))
    mentioning: list[str] = [
        paragraph
        for paragraph in paragraphs
        if any(label in paragraph for label in WIDGET_SECTION_LABELS)
    ]
    assert len(mentioning) >= 3
    for paragraph in mentioning:
        turn_on: int = paragraph.find(f"{WEB_CHAT_CARD} → {TURN_ON}")
        if turn_on == -1:
            turn_on = paragraph.find(f"карточка {WEB_CHAT_CARD} → {TURN_ON}")
        assert turn_on != -1, paragraph
        first_widget_label: int = min(
            paragraph.find(label)
            for label in WIDGET_SECTION_LABELS
            if label in paragraph
        )
        assert turn_on < first_widget_label, paragraph


def test_the_guide_explains_how_a_business_whatsapp_number_is_reached() -> None:
    # The cabinet has no Embedded Signup: the business shares its WhatsApp
    # Business account with the platform's portfolio and system user.
    guide: str = read(LAUNCH_GUIDE)
    section: str = guide.split("### 4.5.", 1)[1].split("### 4.6.", 1)[0]
    workspace: str = read("web/src/i18n/messages/sections/workspace.ts")

    assert "(Embedded Signup)" not in workspace
    assert "Embedded Signup)" not in section.replace("(Embedded Signup) в кабинете", "")
    assert "Партнёры" in section
    assert "Системные пользователи" in section
    assert "whatsapp_business_management" in section


def test_a_new_dpa_version_is_switched_on_with_a_rebuild() -> None:
    # docs/** builds nothing on Render, and "Save and deploy" reuses the old
    # image without the new text.
    for path in (LAUNCH_GUIDE, "render.yaml", "docs/legal/README.md"):
        # Lines of prose and of YAML comments joined.
        text: str = re.sub(r"\s*\n\s*#?\s*", " ", read(path))
        assert "Save, rebuild, and deploy" in text, path
        assert "Deploy latest commit" in text, path


def readme_api_routes() -> set[tuple[str, str]]:
    """(method, path) pairs named in the "## HTTP API" table of README.md."""

    lines: list[str] = read(README).splitlines()
    routes: set[tuple[str, str]] = set()
    for line in lines[lines.index("## HTTP API") + 1 :]:
        if line.startswith("## "):
            break
        cells: list[str] = line.split("|")
        if not line.startswith("|") or len(cells) < 4:
            continue
        for methods, raw_path in re.findall(
            r"`((?:[A-Z]+·)*[A-Z]+) ([^`\s]+)`", cells[2]
        ):
            path: str = (
                raw_path.split("[?", 1)[0]
                .split("?", 1)[0]
                .replace("…", BUSINESS_PREFIX)
            )
            optional = re.search(r"\[([^\]]*)\]", path)
            variants: list[str] = (
                [path]
                if optional is None
                else [
                    path[: optional.start()] + path[optional.end() :],
                    path[: optional.start()]
                    + optional.group(1)
                    + path[optional.end() :],
                ]
            )
            for method in methods.split("·"):
                routes.update(
                    (method, re.sub(r"\{[^}]*\}", "{}", variant))
                    for variant in variants
                )

    return routes


def test_the_readme_api_table_lists_every_described_route() -> None:
    described: set[tuple[str, str]] = {
        (method.upper(), re.sub(r"\{[^}]*\}", "{}", path))
        for path, operations in json.loads(read(OPENAPI_DESCRIPTION))["paths"].items()
        for method in operations
        if method.upper() in HTTP_METHODS
    }
    listed: set[tuple[str, str]] = readme_api_routes()

    assert described - listed == set()
    assert {path for _, path in listed - described} <= UNDESCRIBED_ROUTES
