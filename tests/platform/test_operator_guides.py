"""The launch guide and the README name only what exists and explain the setup."""

import json
import re
from pathlib import Path

from app.utilities.channels.channel_endpoints import (
    WIDGET_DEMO_PATH,
    WIDGET_SCRIPT_PATH,
)
from tests.platform.deployment_variables import (
    COMPOSE_VARIABLES,
    DEPLOYMENT_VARIABLES,
    render_services,
)
from tests.platform.environment_sources import (
    LAUNCH_GUIDE,
    README,
    ROOT,
    VARIABLE_NAME,
    backend_variables,
    cabinet_variables,
    read,
)

# The API's routes as the cabinet's generated client knows them.
OPENAPI_DESCRIPTION: str = "web/openapi.json"

# Routes outside the OpenAPI description (include_in_schema=False).
UNDESCRIBED_ROUTES: frozenset[str] = frozenset(
    {"/healthz", WIDGET_SCRIPT_PATH, WIDGET_DEMO_PATH}
)

# The guide names the curated country data relative to this folder.
REGISTRIES: Path = ROOT / "app" / "registries"


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
