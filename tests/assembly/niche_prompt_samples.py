"""
A sample Tbilisi business for every real niche template, and the chat and
phone instructions assembled for it: the golden prompt snapshots in
tests/assembly/snapshots/ (rewrite them with
`uv run python -m scripts.update_prompt_snapshots`).

Everything is built by code from fixed values (no clock, no randomness),
so a snapshot changes only when a template, a section or the fact table
changes, and the change is reviewed as a diff.
"""

from pathlib import Path

from typed_time_provider import Microseconds, WallClock

from app.registries.localization.country_registry import CountryRegistry
from app.registries.localization.language_registry import LanguageRegistry
from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessLinkKind, Weekday
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import QuestionAnswerType
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessAddress,
    BusinessContacts,
    BusinessLink,
    BusinessProfileDocument,
    ProfileAnswer,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.assistants.assembly_sources import (
    AssistantInstructionSource,
    BusinessFactsSource,
)
from app.schemas.dto.localization import CountryProfile
from app.schemas.dto.niches import NicheTemplate, QuestionDefinition
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import (
    MinNoticeMinutes,
    PartySize,
    ResourceCapacity,
    SlotDurationMinutes,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.strings import AddressText, BusinessName, CityName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.profiles.strings import (
    CancellationPolicyText,
    ProfileAnswerText,
)
from app.transformers.assembly.assistant_instruction_transformer import (
    AssistantInstructionTransformer,
)
from app.transformers.assembly.business_facts_transformer import (
    BusinessFactsTransformer,
)
from app.transformers.assembly.phone_instruction_transformer import (
    PhoneInstructionTransformer,
)
from app.utilities.assembly.assistant_tools import select_assistant_tools
from tests.assembly.builders import build_menu_item, interval

SNAPSHOT_DIRECTORY: Path = Path(__file__).resolve().parent / "snapshots"
SAMPLE_TODAY: LocalDate = LocalDate("2026-10-01")
SAMPLE_NOW_NANOSECONDS: int = 1_790_845_200_000_000_000
LANGUAGES: list[LanguageTag] = [LanguageTag("ka"), LanguageTag("ru"), LanguageTag("en")]
SAMPLE_ANSWERS: dict[QuestionAnswerType, str] = {
    QuestionAnswerType.SHORT_TEXT: "As written in the profile",
    QuestionAnswerType.LONG_TEXT: "The owner's full answer, as written.",
    QuestionAnswerType.NUMBER: "20",
    QuestionAnswerType.URL: "https://example.ge/details",
    QuestionAnswerType.PHONE_NUMBER: "+995555123456",
}


def build_country() -> CountryProfile:
    wall_clock = WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: SAMPLE_NOW_NANOSECONDS,
    )
    registry = CountryRegistry(LanguageRegistry(), wall_clock, DataRegion.EU, [])
    return registry.get(CountryCode("GE"))


def build_sample_business(niche: NicheTemplate) -> BusinessDocument:
    return BusinessDocument(
        name=BusinessName(f"Sample {niche.key.value.replace('_', ' ')}"),
        niche_key=niche.key,
        country_code=CountryCode("GE"),
        city=CityName("Tbilisi"),
        timezone=TimezoneName("Asia/Tbilisi"),
        currency_code=CurrencyCode("GEL"),
        languages=list(LANGUAGES),
        default_language=LANGUAGES[0],
        owner_language=LANGUAGES[0],
        plan_key=PlanKey.VOICE_AND_CHAT,
        data_region=DataRegion.EU,
        members=[],
    )


def sample_answer(question: QuestionDefinition) -> str:
    if question.choices:
        return str(question.choices[0].key)

    return SAMPLE_ANSWERS[question.answer_type]


def build_sample_profile(
    business: BusinessDocument, niche: NicheTemplate
) -> BusinessProfileDocument:
    return BusinessProfileDocument(
        business_id=business.id,
        niche_key=niche.key,
        answers_language=LanguageTag("en"),
        address=BusinessAddress(
            text=AddressText("Rustaveli Ave 10, Tbilisi"),
            maps_url=WebLink("https://maps.example.com/rustaveli-10"),
        ),
        hours=[
            *(interval(weekday, "09:00", "19:00") for weekday in list(Weekday)[:5]),
            interval(Weekday.SATURDAY, "10:00", "16:00"),
        ],
        contacts=BusinessContacts(
            public_phone_number=E164PhoneNumber("+995322123456"),
        ),
        booking_rules=(
            BookingRules(
                resource_kind=niche.resource_kind,
                slot_minutes=SlotDurationMinutes(60),
                max_party_size=PartySize(8),
                min_notice_minutes=MinNoticeMinutes(60),
                deposit_minor=MoneyAmountMinor(2000),
                cancellation_policy=CancellationPolicyText(
                    "Free up to 24 hours before"
                ),
            )
            if niche.takes_bookings
            else None
        ),
        links=[
            BusinessLink(
                kind=BusinessLinkKind.WEBSITE, url=WebLink("https://example.ge")
            ),
            BusinessLink(
                kind=BusinessLinkKind.BOOKING_PAGE,
                url=WebLink("https://example.ge/book"),
            ),
        ],
        niche_answers=[
            ProfileAnswer(
                question_key=question.key,
                answer=ProfileAnswerText(sample_answer(question)),
            )
            for question in niche.questions
        ],
    )


def build_sample_items(
    business: BusinessDocument, niche: NicheTemplate
) -> list[KnowledgeItemDocument]:
    items: list[KnowledgeItemDocument] = []
    for kind in niche.knowledge_kinds:
        if kind is KnowledgeItemKind.FAQ:
            items.append(
                build_menu_item(
                    business, "Is there parking?", None, kind=kind, body="Yes, free."
                )
            )
        elif kind is KnowledgeItemKind.POLICY:
            items.append(
                build_menu_item(
                    business, "Payment", None, kind=kind, body="Cash and cards."
                )
            )
        else:
            label: str = kind.value.replace("_", " ").capitalize()
            items.append(build_menu_item(business, f"{label} A", 2500, kind=kind))
            items.append(
                build_menu_item(
                    business, f"{label} B", 4050, kind=kind, duration_minutes=90
                )
            )

    return items


def build_sample_source(niche: NicheTemplate) -> AssistantInstructionSource:
    """Everything both instructions of the niche's sample business come from."""

    business: BusinessDocument = build_sample_business(niche)
    profile: BusinessProfileDocument = build_sample_profile(business, niche)
    country: CountryProfile = build_country()
    language_registry = LanguageRegistry()
    language_profiles = [language_registry.get(tag) for tag in LANGUAGES]
    items: list[KnowledgeItemDocument] = build_sample_items(business, niche)
    resources: list[ResourceDocument] = (
        [
            ResourceDocument(
                business_id=business.id,
                kind=niche.resource_kind,
                name=ResourceName("Main"),
                capacity=ResourceCapacity(8),
            )
        ]
        if niche.takes_bookings
        else []
    )
    facts = BusinessFactsTransformer().transform(
        BusinessFactsSource(
            business=business,
            profile=profile,
            niche=niche,
            country=country,
            language_profiles=language_profiles,
            knowledge_items=items,
            resources=resources,
            schedule_exceptions=[],
            today=SAMPLE_TODAY,
        )
    )
    return AssistantInstructionSource(
        business=business,
        profile=profile,
        niche=niche,
        country=country,
        language_profiles=language_profiles,
        facts=facts,
        tools=select_assistant_tools(
            takes_bookings=niche.takes_bookings, has_links=True
        ),
        knowledge_items=items,
    )


def render_sample_prompts() -> dict[str, str]:
    """Snapshot file name -> instruction text, for every real niche."""

    prompts: dict[str, str] = {}
    for niche in NicheTemplateRegistry().list_all():
        source = build_sample_source(niche)
        chat = str(AssistantInstructionTransformer().transform(source))
        phone = str(PhoneInstructionTransformer().transform(source))
        prompts[f"{niche.key.value}.chat.txt"] = chat + "\n"
        prompts[f"{niche.key.value}.phone.txt"] = phone + "\n"

    return prompts


def write_prompt_snapshots() -> list[Path]:
    """Rewrite every snapshot file; returns the files written."""

    SNAPSHOT_DIRECTORY.mkdir(exist_ok=True)
    written: list[Path] = []
    for file_name, text in render_sample_prompts().items():
        path = SNAPSHOT_DIRECTORY / file_name
        path.write_text(text, encoding="utf-8")
        written.append(path)

    return written
