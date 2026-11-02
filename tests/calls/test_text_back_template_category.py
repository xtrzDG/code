"""
A text-back is a service message: the WhatsApp template the owner names
for it must not be in Meta's MARKETING category (VOICE-09). The business's
WhatsApp account is asked when the name changes; where it cannot be asked
the name is kept (Meta's own warning still reaches the WHATSAPP_QUALITY
alert).
"""

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.clients.meta.meta_template_catalog_client import MetaTemplateCatalogClient
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.whatsapp_templates import WhatsAppTemplateCategory
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)
from tests.calls.call_steps import save_call_settings
from tests.calls.calls_http import build_calls_http_client
from tests.calls.template_catalog_fakes import FakeTemplateCatalog
from tests.channels.channels_payloads import bearer
from tests.channels.voice_setup import VoiceSetup, build_voice_setup

ACCOUNT: str = "102290129340398"
NUMBER_TOKEN: str = "EAAG-number-token"
MARKETING: list[WhatsAppTemplateCategory] = [WhatsAppTemplateCategory.MARKETING]
UTILITY: list[WhatsAppTemplateCategory] = [WhatsAppTemplateCategory.UTILITY]


@pytest.fixture
def setup() -> VoiceSetup:
    voice_setup = build_voice_setup()
    channel = voice_setup.testbed.add_channel(
        voice_setup.business.id,
        ChannelKind.WHATSAPP,
        "15550001111",
        secret=NUMBER_TOKEN,
    )
    channel.whatsapp_business_account_id = WhatsAppBusinessAccountId(ACCOUNT)
    voice_setup.testbed.channel_repo.save(channel)
    return voice_setup


def name_template(client: TestClient, setup: VoiceSetup, name: str) -> Any:
    return client.put(
        f"/v1/businesses/{setup.business.id}/call-settings",
        json={"is_text_back_enabled": True, "text_back_template_name": name},
        headers=bearer("owner"),
    )


def stored_name(setup: VoiceSetup) -> str | None:
    stored = setup.testbed.call_settings_repo.get_by_business(setup.business.id)
    return None if stored is None else str(stored.text_back_template_name)


def test_a_marketing_template_is_refused(setup: VoiceSetup) -> None:
    catalog = FakeTemplateCatalog({"spring_offer": MARKETING})
    client = build_calls_http_client(setup.testbed, catalog)

    response = name_template(client, setup, "spring_offer")

    assert response.status_code == 422, response.text
    assert [reason["code"] for reason in response.json()["reasons"]] == [
        "marketing_template"
    ]
    assert stored_name(setup) is None
    # Asked with the number's own token, about its own account.
    assert catalog.asked == [(NUMBER_TOKEN, ACCOUNT, "spring_offer")]


def test_a_name_marketing_in_one_language_is_refused_too(setup: VoiceSetup) -> None:
    catalog = FakeTemplateCatalog({"missed_call": [*UTILITY, *MARKETING]})
    client = build_calls_http_client(setup.testbed, catalog)

    assert name_template(client, setup, "missed_call").status_code == 422


def test_a_utility_template_is_kept(setup: VoiceSetup) -> None:
    client = build_calls_http_client(
        setup.testbed, FakeTemplateCatalog({"missed_call": UTILITY})
    )

    response = name_template(client, setup, "missed_call")

    assert response.status_code == 200, response.text
    assert stored_name(setup) == "missed_call"


def test_the_stored_name_is_not_asked_again(setup: VoiceSetup) -> None:
    save_call_settings(setup, template_name="missed_call")
    catalog = FakeTemplateCatalog({"missed_call": MARKETING})
    client = build_calls_http_client(setup.testbed, catalog)

    response = name_template(client, setup, "missed_call")

    assert response.status_code == 200, response.text
    assert catalog.asked == []


def test_where_meta_cannot_be_asked_the_name_is_kept(
    setup: VoiceSetup, caplog: pytest.LogCaptureFixture
) -> None:
    client = build_calls_http_client(
        setup.testbed, FakeTemplateCatalog(is_unreachable=True)
    )

    response = name_template(client, setup, "missed_call")

    assert response.status_code == 200, response.text
    assert stored_name(setup) == "missed_call"
    assert "category of WhatsApp template missed_call" in caplog.text


def test_a_number_without_its_business_account_is_not_asked() -> None:
    setup = build_voice_setup()
    setup.testbed.add_channel(setup.business.id, ChannelKind.WHATSAPP, "15550001111")
    catalog = FakeTemplateCatalog({"missed_call": MARKETING})
    client = build_calls_http_client(setup.testbed, catalog)

    assert name_template(client, setup, "missed_call").status_code == 200
    assert catalog.asked == []


def test_the_graph_client_matches_the_exact_name() -> None:
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "data": [
                    {"name": "missed_call", "category": "UTILITY", "language": "it"},
                    {"name": "missed_call", "category": "MARKETING", "language": "en"},
                    {"name": "missed_call_v2", "category": "MARKETING"},
                    {"name": "missed_call", "category": "SOMETHING_NEW"},
                ]
            },
        )

    client = MetaTemplateCatalogClient(transport=httpx.MockTransport(answer))

    categories = client.find_categories(
        ChannelSecret("token"),
        WhatsAppBusinessAccountId(ACCOUNT),
        WhatsAppTemplateName("missed_call"),
    )

    assert categories == [
        WhatsAppTemplateCategory.UTILITY,
        WhatsAppTemplateCategory.MARKETING,
    ]
    [request] = requests
    assert request.url.path.endswith(f"/{ACCOUNT}/message_templates")
    assert request.url.params["name"] == "missed_call"
    # The token travels in the header, never in the address.
    assert request.headers["Authorization"] == "Bearer token"
    assert "token" not in str(request.url)
