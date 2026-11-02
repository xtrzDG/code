"""
The widget's footer links to the platform's accessibility statement in the
visitor's language (every interface language has the label), through
GET /widget/accessibility, which sends the browser to the public site's
/{locale}/accessibility.
"""

import json
import re
import shutil
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.widget_accessibility_routes import (
    PUBLIC_SITE_LOCALES,
    WIDGET_ACCESSIBILITY_PATH,
    build_widget_accessibility_router,
    public_site_locale,
)
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from tests.channels.test_widget_script_texts import read_script_texts
from tests.channels.widget_node_runner import (
    extract_function,
    extract_variable,
    run_in_node,
)
from tests.channels.widget_script_source import SCRIPT_SOURCE

WEB_I18N_CONFIG: Path = (
    Path(__file__).resolve().parents[2] / "web" / "src" / "i18n" / "config.ts"
)


def build_client(base: str | None = "https://assistant.example/") -> TestClient:
    application = FastAPI()
    install_error_handlers(application)
    application.include_router(
        build_widget_accessibility_router(None if base is None else CabinetBaseUrl(base))
    )
    return TestClient(application, follow_redirects=False)


@pytest.mark.parametrize(
    ("language", "locale"),
    [("it", "it"), ("it-IT", "it"), ("IT_ch", "it"), ("fr", "en"), (None, "en")],
)
def test_the_statement_opens_in_the_sites_locale(
    language: str | None, locale: str
) -> None:
    params = {} if language is None else {"language": language}

    response = build_client().get(WIDGET_ACCESSIBILITY_PATH, params=params)

    assert response.status_code == 302
    assert response.headers["location"] == (
        f"https://assistant.example/{locale}/accessibility"
    )
    assert response.headers["cache-control"] == "public, max-age=86400"


def test_odd_languages_and_a_missing_site() -> None:
    assert public_site_locale("x" * 100) == "en"
    assert public_site_locale("<script>") == "en"
    assert build_client(None).get(WIDGET_ACCESSIBILITY_PATH).status_code == 404


def test_the_locales_are_the_public_sites() -> None:
    config: str = WEB_I18N_CONFIG.read_text(encoding="utf-8")
    match = re.search(r"export const LOCALES = \[(.*?)\] as const;", config)
    assert match is not None
    assert tuple(re.findall(r'"([a-z]+)"', match.group(1))) == PUBLIC_SITE_LOCALES


def test_every_interface_language_names_the_statement() -> None:
    texts = read_script_texts()

    assert texts
    for language, keys in texts.items():
        assert "accessibility" in keys, language
    assert 'var ACCESSIBILITY_PATH = "/widget/accessibility";' in SCRIPT_SOURCE


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_the_footer_links_the_statement_in_a_new_tab() -> None:
    program: str = (
        extract_variable("WEB_LINK_PATTERN")
        + extract_variable("ACCESSIBILITY_PATH")
        + extract_function("el")
        + extract_function("isSafeWebLink")
        + extract_function("footerLink")
        + extract_function("accessibilityUrl")
        + extract_function("buildFooter")
        + "\nvar apiBase = 'https://api.example';"
        + "\nvar state = { language: 'it' };"
        + "\nvar config = { privacy_url: 'javascript:alert(1)',"
        + " powered_by_url: 'https://assistant.example/?ref=X' };"
        + "\nvar footer = buildFooter();"
        + "\nconsole.log(JSON.stringify(describe(footer.row)));"
    )

    row = cast(dict[str, Any], run_in_node(program))

    links = [child for child in row["children"] if child.get("tag") == "a"]
    by_class = {link["className"]: link for link in links}
    # A privacy address that is not a web page is no link at all.
    assert "aw-privacy" not in by_class
    statement = by_class["aw-accessibility"]
    assert statement["href"] == (
        "https://api.example/widget/accessibility?language=it"
    )
    assert statement["target"] == "_blank"
    assert statement["rel"] == "noopener noreferrer"
    assert by_class["aw-powered"]["href"] == "https://assistant.example/?ref=X"
    assert json.dumps(row).count("javascript:") == 0
