"""
The hosted chat's privacy notice states how calls are recorded when the
business's AI assistant answers its phone (over HTTP, the whole application).
"""

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.localization.constrained_strings import CountryCode
from tests.e2e.harness import Workshop
from tests.sharing.sharing_steps import SharedBusiness, create_business, share_links

OWNER_PHONE: str = "+995 555 11 22 33"


def answer_calls(
    workshop: Workshop,
    business: SharedBusiness,
    *,
    country: str | None = None,
    phone_status: ChannelStatus = ChannelStatus.CONNECTED,
) -> None:
    """A live voice version and the business's phone number."""

    container = workshop.container
    business_id = BusinessId(business.business_id)
    with container.utilities.storage_scope().scoped_to_business(business_id):
        stored: BusinessDocument | None = container.repositories.business_repo().get(
            business_id
        )
        assert stored is not None
        version = AssistantVersionDocument(
            business_id=business_id,
            version_number=AssistantVersionNumber(1),
            niche_key=NicheKey.RESTAURANT,
            model_id=LlmModelId("gpt-5-mini"),
            prompt_text=SystemPromptText("Prompt"),
            tools=[AssistantToolName.CREATE_BOOKING],
            languages=stored.languages,
            default_language=stored.default_language,
            is_voice_enabled=True,
            facts=[],
            profile_revision=Microseconds(1),
        )
        container.repositories.assistant_version_repo().save(version)
        stored.published_assistant_version_id = version.id
        if country is not None:
            stored.country_code = CountryCode(country)
        container.repositories.business_repo().save(stored)
        container.repositories.channel_repo().save(
            ChannelDocument(
                business_id=business_id,
                kind=ChannelKind.PHONE,
                external_id=ChannelExternalId("+995322000000"),
                status=phone_status,
            )
        )


def public_chat(workshop: Workshop, business: SharedBusiness) -> dict[str, object]:
    slug = share_links(workshop, business)["slug"]
    response = workshop.client.get(f"/v1/public/chat/{slug}")
    assert response.status_code == 200, response.text
    view: dict[str, object] = response.json()
    return view


def test_a_chat_only_business_says_nothing_about_calls(workshop: Workshop) -> None:
    business = create_business(workshop, OWNER_PHONE, "Cafe Batumi")

    assert public_chat(workshop, business)["phone_calls"] is None


def test_a_notice_country_states_that_calls_are_recorded(workshop: Workshop) -> None:
    business = create_business(workshop, OWNER_PHONE, "Cafe Batumi")
    answer_calls(workshop, business)

    assert public_chat(workshop, business)["phone_calls"] == {
        "recording_consent_rule": "notice",
        "recording_retention_days": 90,
    }


def test_an_all_party_consent_country_states_that_callers_are_asked(
    workshop: Workshop,
) -> None:
    business = create_business(workshop, OWNER_PHONE, "Café Berlin")
    answer_calls(workshop, business, country="DE")

    assert public_chat(workshop, business)["phone_calls"] == {
        "recording_consent_rule": "all_party_consent",
        "recording_retention_days": 90,
    }


def test_a_disconnected_number_takes_no_calls(workshop: Workshop) -> None:
    business = create_business(workshop, OWNER_PHONE, "Cafe Batumi")
    answer_calls(workshop, business, phone_status=ChannelStatus.ERROR)

    assert public_chat(workshop, business)["phone_calls"] is None
