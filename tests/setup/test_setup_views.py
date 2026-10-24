"""Phone links and pending changes as pure rules."""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.businesses.booleans import IsVoiceEnabled
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.utilities.setup.pending_changes import has_unapplied_changes
from app.utilities.setup.setup_views import phone_test_links

BUILT_AT: Microseconds = Microseconds(1_790_000_000_000_000)
BUSINESS = BusinessDocument(
    name=BusinessName("Salobie Bia"),
    niche_key=NicheKey.RESTAURANT,
    country_code=CountryCode("GE"),
    timezone=TimezoneName("Asia/Tbilisi"),
    currency_code=CurrencyCode("GEL"),
    languages=[LanguageTag("ka"), LanguageTag("en")],
    default_language=LanguageTag("ka"),
    owner_language=LanguageTag("ka"),
    plan_key=PlanKey.CHAT,
    data_region=DataRegion.EU,
    members=[],
)


def channel(
    kind: ChannelKind,
    external_id: str | None = None,
    status: ChannelStatus = ChannelStatus.CONNECTED,
) -> ChannelDocument:
    return ChannelDocument(
        business_id=BUSINESS.id,
        kind=kind,
        external_id=None if external_id is None else ChannelExternalId(external_id),
        status=status,
    )


def version() -> AssistantVersionDocument:
    return AssistantVersionDocument(
        business_id=BUSINESS.id,
        version_number=AssistantVersionNumber(1),
        niche_key=NicheKey.RESTAURANT,
        model_id=LlmModelId("scripted"),
        prompt_text=SystemPromptText("You answer for Salobie Bia."),
        tools=[],
        languages=list(BUSINESS.languages),
        default_language=BUSINESS.default_language,
        is_voice_enabled=IsVoiceEnabled(False),
        facts=[],
        profile_revision=BUILT_AT,
        created_at=BUILT_AT,
        updated_at=BUILT_AT,
    )


def profile(updated_at: Microseconds) -> BusinessProfileDocument:
    return BusinessProfileDocument(
        business_id=BUSINESS.id,
        niche_key=NicheKey.RESTAURANT,
        answers_language=LanguageTag("ka"),
        created_at=BUILT_AT,
        updated_at=updated_at,
    )


def test_the_website_chat_link_needs_a_public_https_api() -> None:
    web_chat = [channel(ChannelKind.WEB_CHAT)]

    secure = phone_test_links(
        BUSINESS, web_chat, PublicBaseUrl("https://api.example/"), is_live=False
    )
    local = phone_test_links(
        BUSINESS, web_chat, PublicBaseUrl("http://localhost:8000"), is_live=True
    )
    unset = phone_test_links(BUSINESS, web_chat, None, is_live=True)

    assert [str(link.url) for link in secure] == [
        f"https://api.example/widget/demo?business_id={BUSINESS.id}&language=ka"
    ]
    assert local == []
    assert unset == []


def test_only_connected_channels_with_a_bot_name_give_links() -> None:
    channels = [
        channel(ChannelKind.WEB_CHAT, status=ChannelStatus.PENDING),
        channel(ChannelKind.TELEGRAM, external_id=None),
        channel(ChannelKind.WHATSAPP, external_id="995555123456"),
    ]

    links = phone_test_links(
        BUSINESS, channels, PublicBaseUrl("https://api.example"), is_live=True
    )

    assert links == []


def test_before_the_first_go_live_a_saved_profile_is_a_change_to_apply() -> None:
    assert has_unapplied_changes(BUSINESS, None, None, [], [], []) is False
    assert has_unapplied_changes(BUSINESS, None, profile(BUILT_AT), [], [], []) is True


def test_changes_after_the_live_version_was_built_are_pending() -> None:
    live = version()
    newer_profile = profile(Microseconds(int(BUILT_AT) + 1))
    other_languages = BUSINESS.model_copy(update={"languages": [LanguageTag("ka")]})
    other_default = BUSINESS.model_copy(update={"default_language": LanguageTag("en")})

    assert has_unapplied_changes(BUSINESS, live, profile(BUILT_AT), [], [], []) is False
    assert has_unapplied_changes(BUSINESS, live, newer_profile, [], [], []) is True
    assert has_unapplied_changes(other_languages, live, None, [], [], []) is True
    assert has_unapplied_changes(other_default, live, None, [], [], []) is True
