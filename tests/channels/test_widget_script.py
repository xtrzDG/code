"""The website chat widget script, its demo page and their agreement with the API."""

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.application import build_http_application
from app.gateways.http.cabinet_cors_middleware import is_self_cors_path
from app.gateways.http.channel_routes import WIDGET_CONFIG_PATH, WIDGET_MESSAGES_PATH
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.widget_cors_middleware import (
    WIDGET_CORS_HEADERS,
    WIDGET_SESSION_KEY_HEADER,
)
from app.gateways.http.widget_script_routes import (
    STATIC_DIRECTORY,
    WIDGET_SCRIPT_FILE_NAME,
    build_widget_script_router,
)
from app.registries.localization.curated_country_languages import (
    CURATED_CUSTOMER_LANGUAGES,
)
from app.schemas.typings.channels.constrained_strings import (
    PublicBaseUrl,
    WidgetMessageText,
    WidgetSessionKey,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.channel_endpoints import (
    WIDGET_BUSINESS_ATTRIBUTE,
    WIDGET_DEMO_PATH,
    WIDGET_SCRIPT_PATH,
)
from app.utilities.channels.widget_texts import WIDGET_GREETING, build_widget_greeting
from app.utilities.localization.language_tags import base_language_code
from tests.channels.testbed import ChannelsTestbed, bearer
from tests.e2e.harness import start_workshop

SCRIPT_SOURCE: str = (STATIC_DIRECTORY / WIDGET_SCRIPT_FILE_NAME).read_text(
    encoding="utf-8"
)
BUSINESS_ID: str = "business_0b6c2f5e-1d1a-4c55-9a3e-2f1d5b7c9e01"


def build_client() -> TestClient:
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(build_widget_script_router())
    return TestClient(http_application)


def read_script_constant(name: str) -> str:
    match = re.search(rf'var {name} = "([^"]*)";', SCRIPT_SOURCE)
    assert match is not None, name
    return match.group(1)


def read_script_number(name: str) -> int:
    match = re.search(rf"var {name} = ([0-9]+);", SCRIPT_SOURCE)
    assert match is not None, name
    return int(match.group(1))


class ScriptTagParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.script_tags: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            self.script_tags.append(dict(attrs))


def parse_script_tags(markup: str) -> list[dict[str, str | None]]:
    parser = ScriptTagParser()
    parser.feed(markup)
    return parser.script_tags


class TestWidgetScriptRoute:
    def test_script_is_served_as_javascript_for_any_site(self) -> None:
        response = build_client().get(
            WIDGET_SCRIPT_PATH, headers={"Origin": "https://cafe.example"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/javascript; charset=utf-8"
        assert response.headers["access-control-allow-origin"] == "*"
        assert response.headers["cross-origin-resource-policy"] == "cross-origin"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "public" in response.headers["cache-control"]
        assert "max-age=300" in response.headers["cache-control"]
        assert "set-cookie" not in response.headers
        assert response.text == SCRIPT_SOURCE

    def test_head_answers_with_the_headers_only(self) -> None:
        response = build_client().head(WIDGET_SCRIPT_PATH)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/javascript; charset=utf-8"
        assert response.content == b""

    def test_unchanged_script_is_revalidated_with_its_etag(self) -> None:
        client = build_client()
        etag = client.get(WIDGET_SCRIPT_PATH).headers["etag"]

        cached = client.get(WIDGET_SCRIPT_PATH, headers={"If-None-Match": etag})
        weak = client.get(WIDGET_SCRIPT_PATH, headers={"If-None-Match": f"W/{etag}"})
        stale = client.get(WIDGET_SCRIPT_PATH, headers={"If-None-Match": '"old"'})

        assert cached.status_code == 304
        assert cached.content == b""
        assert cached.headers["etag"] == etag
        assert weak.status_code == 304
        assert stale.status_code == 200

    def test_cabinet_cors_allow_list_does_not_apply_to_the_script(self) -> None:
        http_application = build_http_application(
            routers=[build_widget_script_router()],
            error_reporter=_SilentErrorReporter(),
            cors_allowed_origins=[PublicBaseUrl("https://cabinet.example")],
        )

        response = TestClient(http_application).get(
            WIDGET_SCRIPT_PATH, headers={"Origin": "https://salon.example"}
        )

        assert is_self_cors_path(WIDGET_SCRIPT_PATH)
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "*"

    def test_the_application_serves_the_script_and_the_demo(self) -> None:
        workshop = start_workshop()

        with workshop.client as client:
            script = client.get(WIDGET_SCRIPT_PATH)
            demo = client.get(WIDGET_DEMO_PATH, params={"business_id": BUSINESS_ID})

        assert script.status_code == 200
        assert script.text == SCRIPT_SOURCE
        assert demo.status_code == 200
        assert "/widget.js" not in workshop.application.openapi()["paths"]


class TestScriptAgreesWithTheApi:
    def test_paths_and_attribute_match_the_routes(self) -> None:
        assert read_script_constant("BUSINESS_ATTRIBUTE") == WIDGET_BUSINESS_ATTRIBUTE
        assert read_script_constant("CONFIG_PATH") == WIDGET_CONFIG_PATH
        assert read_script_constant("MESSAGES_PATH") == WIDGET_MESSAGES_PATH
        assert read_script_constant("SCRIPT_FILE_NAME") == WIDGET_SCRIPT_PATH

    def test_session_keys_and_message_limit_fit_the_request_schema(self) -> None:
        alphabet = read_script_constant("SESSION_KEY_ALPHABET")
        generated_key = "v1_" + (alphabet * 2)[:32]

        assert WidgetSessionKey(generated_key) == generated_key
        assert len(set(alphabet)) == len(alphabet) == 64
        assert read_script_number("MAX_MESSAGE_LENGTH") == WidgetMessageText.max_length

    def test_script_keeps_no_cookies_and_writes_no_html(self) -> None:
        assert "document.cookie" not in SCRIPT_SOURCE
        assert "innerHTML" not in SCRIPT_SOURCE
        assert 'credentials: "omit"' in SCRIPT_SOURCE
        assert "attachShadow" in SCRIPT_SOURCE

    def test_snippet_from_the_cabinet_loads_this_script(self) -> None:
        testbed = ChannelsTestbed()
        owner_id = testbed.add_user("owner")
        business = testbed.add_business(owner_id)

        snippet_response = testbed.build_http_client().get(
            f"/v1/businesses/{business.id}/channels/web/snippet",
            headers=bearer("owner"),
        )

        assert snippet_response.status_code == 200
        [tag] = parse_script_tags(snippet_response.json()["snippet"])
        script_url = tag["src"]
        assert script_url is not None
        assert script_url == snippet_response.json()["script_url"]
        assert tag[WIDGET_BUSINESS_ATTRIBUTE] == str(business.id)
        assert "async" in tag
        served = build_client().get(urlsplit(script_url).path)
        assert served.status_code == 200
        assert served.text == SCRIPT_SOURCE

    def test_the_visitor_key_header_is_the_one_the_api_reads(self) -> None:
        assert read_script_constant("SESSION_KEY_HEADER") == WIDGET_SESSION_KEY_HEADER
        assert (
            WIDGET_SESSION_KEY_HEADER
            in WIDGET_CORS_HEADERS["Access-Control-Allow-Headers"]
        )
        assert "?session_key=" not in SCRIPT_SOURCE

    def test_the_status_region_is_not_inside_the_hideable_panel(self) -> None:
        # A display:none panel would silence the screen-reader announcements.
        assert "panel.appendChild(status)" not in SCRIPT_SOURCE
        assert "wrapper.appendChild(status)" in SCRIPT_SOURCE
        assert 'text("newReply")' in SCRIPT_SOURCE

    def test_links_in_answers_keep_the_bubble_text_colour(self) -> None:
        assert ".aw-assistant a,.aw-staff a{color:inherit;}" in SCRIPT_SOURCE

    @pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
    def test_script_parses_with_node(self) -> None:
        node = shutil.which("node")
        assert node is not None
        script_path: Path = STATIC_DIRECTORY / WIDGET_SCRIPT_FILE_NAME

        result = subprocess.run(
            [node, "--check", str(script_path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        assert result.returncode == 0, result.stderr


class TestWidgetDemoPage:
    def test_demo_embeds_the_widget_like_the_snippet(self) -> None:
        response = build_client().get(
            WIDGET_DEMO_PATH, params={"business_id": BUSINESS_ID}
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "script-src 'self'" in response.headers["content-security-policy"]
        assert response.headers["cache-control"] == "no-store"
        widget_tags = [
            tag
            for tag in parse_script_tags(response.text)
            if tag.get(WIDGET_BUSINESS_ATTRIBUTE) is not None
        ]
        assert widget_tags == [
            {
                "src": "../widget.js",
                WIDGET_BUSINESS_ATTRIBUTE: BUSINESS_ID,
                "data-preview": "true",
                "data-open": "true",
                "async": None,
            }
        ]
        assert "&lt;script src=" in response.text

    def test_language_can_be_forced_and_bad_values_are_ignored(self) -> None:
        client = build_client()

        hebrew = client.get(
            WIDGET_DEMO_PATH, params={"business_id": BUSINESS_ID, "language": "he"}
        )
        injected = client.get(
            WIDGET_DEMO_PATH,
            params={"business_id": BUSINESS_ID, "language": '"><script>x</script>'},
        )

        [hebrew_tag] = parse_script_tags(hebrew.text)
        assert hebrew_tag["data-language"] == "he"
        [plain_tag] = parse_script_tags(injected.text)
        assert "data-language" not in plain_tag
        assert "<script>x" not in injected.text

    def test_without_a_business_id_the_page_asks_for_one(self) -> None:
        response = build_client().get(WIDGET_DEMO_PATH)

        assert response.status_code == 200
        assert parse_script_tags(response.text) == []
        assert 'name="business_id"' in response.text

    def test_malformed_business_id_is_not_found(self) -> None:
        response = build_client().get(
            WIDGET_DEMO_PATH, params={"business_id": '"><script>alert(1)</script>'}
        )

        assert response.status_code == 404
        assert "<script>" not in response.text


class _SilentErrorReporter:
    def capture_exception(self, error: BaseException) -> None:
        del error


def read_script_texts() -> dict[str, set[str]]:
    """The interface languages of the script and the keys each one has."""

    block: str = SCRIPT_SOURCE[SCRIPT_SOURCE.index("var TEXTS = {") :]
    block = block[: block.index("\n  };")]
    texts: dict[str, set[str]] = {}
    for match in re.finditer(r"\n    ([a-z]+): \{(.*?)\n    \}", block, re.S):
        texts[match.group(1)] = set(re.findall(r"\n      ([A-Za-z]+):", match.group(2)))
    return texts


def read_script_greetings() -> dict[str, str]:
    """The script's own greeting in each of its interface languages."""

    block: str = SCRIPT_SOURCE[SCRIPT_SOURCE.index("var TEXTS = {") :]
    block = block[: block.index("\n  };")]
    greetings: dict[str, str] = {}
    for match in re.finditer(r"\n    ([a-z]+): \{(.*?)\n    \}", block, re.S):
        greeting = re.search(r'\n      greeting: ("(?:[^"\\]|\\.)*")', match.group(2))
        assert greeting is not None, match.group(1)
        greetings[match.group(1)] = json.loads(greeting.group(1))
    return greetings


def run_script_function(function_name: str, call: str) -> str:
    """Run one function of the script in node and return what it prints."""

    node = shutil.which("node")
    assert node is not None
    match = re.search(
        rf"\n  function {function_name}\(.*?\n  \}}\n", SCRIPT_SOURCE, re.S
    )
    assert match is not None, function_name
    result = subprocess.run(
        [node, "-e", f"{match.group(0)}\nconsole.log({call});"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


class TestWidgetTexts:
    def test_every_curated_customer_language_has_complete_interface_texts(
        self,
    ) -> None:
        texts = read_script_texts()
        english_keys = texts["en"]
        curated = {
            base_language_code(tag).lower()
            for tags in CURATED_CUSTOMER_LANGUAGES.values()
            for tag in tags
        }

        assert sorted(code for code in curated if code not in texts) == []
        for code in curated:
            assert texts[code] == english_keys, code

    def test_the_api_greets_in_every_interface_language_of_the_script(
        self,
    ) -> None:
        script_greetings = read_script_greetings()
        api_languages = {str(tag) for tag in WIDGET_GREETING.values}

        assert api_languages == set(script_greetings)
        for language, script_greeting in script_greetings.items():
            # The API's greeting (sent with the widget config) wins over the
            # script's own one, so both say the same thing.
            assert build_widget_greeting(LanguageTag(language), "{business}") == (
                script_greeting
            ), language


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
class TestWidgetColours:
    @pytest.mark.parametrize(
        ("accent", "text_colour"),
        [
            # Mid-tone brand colours: dark text reads better than white.
            ("#f59e0b", "#111827"),
            ("#22c55e", "#111827"),
            ("#06b6d4", "#111827"),
            ("#f97316", "#111827"),
            ("#fde047", "#111827"),
            # Dark colours and the cabinet's presets keep white text.
            ("#4f46e5", "#ffffff"),
            ("#111827", "#ffffff"),
            ("#1d4ed8", "#ffffff"),
            ("#15803d", "#ffffff"),
        ],
    )
    def test_text_on_the_accent_takes_the_higher_contrast(
        self, accent: str, text_colour: str
    ) -> None:
        assert (
            run_script_function("readableTextColor", f'readableTextColor("{accent}")')
            == text_colour
        )


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
class TestWidgetLanguagePicker:
    @pytest.mark.parametrize(
        ("language", "label"),
        [
            ('{tag: "ru", native_name: "русский"}', "Русский"),
            ('{tag: "de", native_name: "Deutsch"}', "Deutsch"),
            # Georgian has no capitals; uppercasing would give Mtavruli.
            ('{tag: "ka", native_name: "ქართული"}', "ქართული"),
            ('{tag: "he", native_name: "עברית"}', "עברית"),
            ('{tag: "xx"}', "Xx"),
        ],
    )
    def test_languages_are_named_with_a_capital_where_the_script_has_one(
        self, language: str, label: str
    ) -> None:
        assert run_script_function("pickerLabel", f"pickerLabel({language})") == label
