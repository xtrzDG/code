"""The website chat's look (PUT .../channels/web) and greetings in its config."""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from typed_time_provider import Microseconds

from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.widget_script_routes import build_widget_script_router
from app.schemas.constants.channels import ChannelKind, WidgetPosition
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.channels.constrained_strings import WidgetAccentColor
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.channel_endpoints import WIDGET_DEMO_PATH
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.widget_texts import build_widget_greeting
from tests.channels.test_widget_script import BUSINESS_ID, parse_script_tags
from tests.channels.testbed import (
    ARMENIA,
    GEORGIA,
    ISRAEL,
    ChannelsTestbed,
    CountrySetup,
    HttpResponse,
    bearer,
)

NIGERIA = CountrySetup("NG", "Africa/Lagos", "NGN", ("yo", "en"))


class WebChatSetup:
    def __init__(self, country: CountrySetup = GEORGIA) -> None:
        self.testbed = ChannelsTestbed()
        owner_id = self.testbed.add_user("owner")
        self.business = self.testbed.add_business(
            owner_id, country=country, name="Funicular VR"
        )
        self.client = self.testbed.build_http_client()

    def put(self, channel: str, body: dict[str, Any]) -> HttpResponse:
        return self.client.put(
            f"/v1/businesses/{self.business.id}/channels/{channel}",
            json=body,
            headers=bearer("owner"),
        )

    def config(self) -> dict[str, Any]:
        response = self.client.get(f"/v1/widget/{self.business.id}/config")
        assert response.status_code == 200
        body: dict[str, Any] = response.json()
        return body


class TestWidgetAppearance:
    def test_colour_and_corner_are_saved_and_kept(self) -> None:
        setup = WebChatSetup()

        saved = setup.put("web", {"widget_color": "#0F766E", "widget_position": "left"})

        assert saved.status_code == 200, saved.text
        assert saved.json()["widget_color"] == "#0F766E"
        assert saved.json()["widget_position"] == "left"
        config = setup.config()
        assert config["accent_color"] == "#0F766E"
        assert config["position"] == "left"

        assert setup.put("web", {}).json()["widget_color"] == "#0F766E"
        moved = setup.put("web", {"widget_position": "right"}).json()
        assert moved["widget_color"] == "#0F766E"
        assert moved["widget_position"] == "right"
        channel = find_business_channel(
            setup.testbed.channel_repo, setup.business.id, ChannelKind.WEB_CHAT
        )
        assert channel is not None
        assert channel.web_chat_appearance is not None
        assert channel.web_chat_appearance.accent_color == WidgetAccentColor("#0F766E")
        assert channel.web_chat_appearance.position is WidgetPosition.RIGHT
        assert (
            setup.testbed.audit_actions(setup.business.id).count(("update", "channel"))
            == 2
        )

    def test_malformed_choices_and_other_channels_are_refused(self) -> None:
        setup = WebChatSetup()

        assert setup.put("web", {"widget_color": "red"}).status_code == 422
        assert setup.put("web", {"widget_color": "#12345"}).status_code == 422
        assert setup.put("web", {"widget_position": "top"}).status_code == 422
        other_channel = setup.put(
            "phone", {"phone_number": "+995 32 200 00 00", "widget_color": "#000000"}
        )
        assert other_channel.status_code == 422
        assert "website chat" in other_channel.json()["message"]

    def test_defaults_are_left_to_the_widget(self) -> None:
        setup = WebChatSetup()

        view = setup.put("web", {}).json()

        assert view["widget_color"] is None
        assert view["widget_position"] is None
        assert setup.config()["accent_color"] is None


class TestWidgetGreetings:
    def test_greetings_follow_the_business_languages_before_publishing(self) -> None:
        setup = WebChatSetup(GEORGIA)
        setup.put("web", {})

        greetings = setup.config()["greetings"]

        assert [item["language"] for item in greetings] == ["ka", "ru", "en"]
        assert greetings[1]["text"] == (
            "Здравствуйте! Я AI-ассистент «Funicular VR». Чем могу помочь?"
        )
        assert greetings[2]["text"] == (
            "Hello! I am the AI assistant of Funicular VR. How can I help you?"
        )
        assert {item["direction"] for item in greetings} == {"ltr"}

    def test_the_live_version_decides_the_languages(self) -> None:
        setup = WebChatSetup(ISRAEL)
        setup.put("web", {})
        publish_version(setup, ["he", "en"])

        greetings = setup.config()["greetings"]

        assert [item["language"] for item in greetings] == ["he", "en"]
        assert greetings[0]["direction"] == "rtl"
        assert "Funicular VR" in greetings[0]["text"]

    def test_the_ai_disclosure_stands_in_and_unknown_languages_are_left_out(
        self,
    ) -> None:
        armenian = WebChatSetup(ARMENIA)
        yoruba = WebChatSetup(NIGERIA)

        armenian_greetings = armenian.config()["greetings"]
        yoruba_greetings = yoruba.config()["greetings"]

        assert armenian_greetings[0] == {
            "language": "hy",
            "text": "Բարև Ձեզ։ Ես Funicular VR-ի AI օգնականն եմ։",
            "direction": "ltr",
        }
        assert [item["language"] for item in yoruba_greetings] == ["en"]

    def test_regional_tags_use_their_base_language(self) -> None:
        assert build_widget_greeting(LanguageTag("pt-BR"), "Café") == (
            "Olá! Sou o assistente de IA de Café. Como posso ajudar?"
        )
        assert build_widget_greeting(LanguageTag("yo"), "Café") is None


class TestWidgetDemoPreview:
    def test_unsaved_colour_and_corner_can_be_previewed(self) -> None:
        client = build_demo_client()

        preview = client.get(
            WIDGET_DEMO_PATH,
            params={"business_id": BUSINESS_ID, "color": "#0f766e", "position": "LEFT"},
        )
        ignored = client.get(
            WIDGET_DEMO_PATH,
            params={
                "business_id": BUSINESS_ID,
                "color": '"><script>x</script>',
                "position": "middle",
            },
        )

        [tag] = parse_script_tags(preview.text)
        assert tag["data-color"] == "#0f766e"
        assert tag["data-position"] == "left"
        [plain] = parse_script_tags(ignored.text)
        assert "data-color" not in plain
        assert "data-position" not in plain
        assert "<script>x" not in ignored.text


def build_demo_client() -> TestClient:
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(build_widget_script_router())
    return TestClient(http_application)


def publish_version(setup: WebChatSetup, languages: list[str]) -> None:
    """A live assistant version answering in `languages`."""

    version = AssistantVersionDocument(
        business_id=setup.business.id,
        version_number=AssistantVersionNumber(1),
        niche_key=NicheKey.ENTERTAINMENT,
        model_id=LlmModelId("gpt-5-mini"),
        prompt_text=SystemPromptText("Prompt"),
        tools=[],
        languages=[LanguageTag(tag) for tag in languages],
        default_language=LanguageTag(languages[0]),
        is_voice_enabled=False,
        facts=[],
        profile_revision=Microseconds(1),
    )
    setup.testbed.assistant_version_repo.save(version)
    setup.business.published_assistant_version_id = version.id
    setup.testbed.business_repo.save(setup.business)
