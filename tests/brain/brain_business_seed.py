"""The business a brain test world serves: owner, staff, version, profile."""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName, AssistantVersionStatus
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import Weekday
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.assistants import AssistantVersionDocument, BusinessFact
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.profiles import BusinessProfileDocument, OpeningInterval
from app.schemas.domain.users import UserDocument
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.profiles.constrained_strings import FactKey
from app.schemas.typings.profiles.strings import FactLabel, FactValue
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.assembly.assistant_tools import CONVERSATION_TOOLS
from tests.brain.brain_repositories import BrainRepositories
from tests.brain.business_setups import BusinessSetup

# Every tool a version can hold (offer_choices is added by the conversation).
ALL_TOOLS: list[AssistantToolName] = [
    tool for tool in AssistantToolName if tool not in CONVERSATION_TOOLS
]


@dataclass(frozen=True)
class SeededBusiness:
    owner_id: UserId
    staff_id: UserId
    business: BusinessDocument
    version: AssistantVersionDocument


def seed_business(
    repos: BrainRepositories,
    setup: BusinessSetup,
    *,
    tools: list[AssistantToolName] | None,
    facts: list[tuple[str, str, str]] | None,
    hours: list[tuple[int, int]] | None,
    is_published: bool,
) -> SeededBusiness:
    owner_id, staff_id = UserId(), UserId()
    for user_id, phone in ((owner_id, "+995599000001"), (staff_id, "+995599000002")):
        repos.user_repo.save(
            UserDocument(
                id=user_id,
                login_method=LoginMethod.PHONE,
                phone_number=E164PhoneNumber(phone),
                locale=LanguageTag("en"),
                is_verified=True,
            )
        )

    business = build_business(setup, owner_id, staff_id)
    version = build_version(business, setup, tools, facts, is_published)
    repos.version_repo.save(version)
    if is_published:
        business.published_assistant_version_id = version.id

    repos.business_repo.save(business)
    # The business's phone number, connected: the phone assistant is on.
    repos.channel_repo.save(
        ChannelDocument(
            business_id=business.id,
            kind=ChannelKind.PHONE,
            external_id=ChannelExternalId("+995322000000"),
            status=ChannelStatus.CONNECTED,
        )
    )
    repos.profile_repo.save(
        BusinessProfileDocument(
            business_id=business.id,
            niche_key=NicheKey.RESTAURANT,
            answers_language=LanguageTag(setup.languages[0]),
            hours=[
                OpeningInterval(
                    weekday=weekday,
                    opens_at=OpeningMinuteOfDay(opens),
                    closes_at=ClosingMinuteOfDay(closes),
                )
                for weekday in Weekday
                for opens, closes in (hours if hours is not None else [(720, 1380)])
            ],
        )
    )
    return SeededBusiness(
        owner_id=owner_id, staff_id=staff_id, business=business, version=version
    )


def build_business(
    setup: BusinessSetup, owner_id: UserId, staff_id: UserId
) -> BusinessDocument:
    return BusinessDocument(
        name=BusinessName(setup.name),
        niche_key=NicheKey.RESTAURANT,
        country_code=CountryCode(setup.country_code),
        timezone=TimezoneName(setup.timezone),
        currency_code=CurrencyCode(setup.currency_code),
        languages=[LanguageTag(tag) for tag in setup.languages],
        default_language=LanguageTag(setup.languages[0]),
        owner_language=LanguageTag(setup.languages[0]),
        plan_key=PlanKey.VOICE_AND_CHAT,
        status=setup.status,
        data_region=DataRegion.EU,
        members=[
            BusinessMember(user_id=owner_id, role=BusinessMemberRole.OWNER),
            BusinessMember(user_id=staff_id, role=BusinessMemberRole.STAFF),
        ],
    )


def build_version(
    business: BusinessDocument,
    setup: BusinessSetup,
    tools: list[AssistantToolName] | None,
    facts: list[tuple[str, str, str]] | None,
    is_published: bool,
) -> AssistantVersionDocument:
    return AssistantVersionDocument(
        business_id=business.id,
        version_number=AssistantVersionNumber(1),
        status=(
            AssistantVersionStatus.PUBLISHED
            if is_published
            else AssistantVersionStatus.READY
        ),
        niche_key=NicheKey.RESTAURANT,
        model_id=LlmModelId("scripted"),
        prompt_text=SystemPromptText(f"You are the AI assistant of {setup.name}."),
        tools=list(ALL_TOOLS if tools is None else tools),
        languages=[LanguageTag(tag) for tag in setup.languages],
        default_language=LanguageTag(setup.languages[0]),
        is_voice_enabled=True,
        facts=[
            BusinessFact(
                key=FactKey(key), label=FactLabel(label), value=FactValue(value)
            )
            for key, label, value in (
                facts
                if facts is not None
                else [
                    (
                        "signature_dish",
                        "Adjarian khachapuri",
                        f"18 {setup.currency_code}",
                    ),
                    ("opening_hours", "Opening hours", "Mon-Sun 12:00-23:00"),
                ]
            )
        ],
        profile_revision=Microseconds(0),
    )
