"""
A Tbilisi restaurant seeded into a testbed: ka, ru, en; GEL prices; a terrace
with its own hours, holidays and a full profile.
"""

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.businesses import BusinessLinkKind, Weekday
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeAttribute
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessAddress,
    BusinessContacts,
    BusinessLink,
    BusinessProfileDocument,
    ProfileAnswer,
)
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import (
    MinNoticeMinutes,
    PartySize,
    ResourceCapacity,
    ResourceUnitCount,
    SlotDurationMinutes,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.strings import ResourceName, ScheduleExceptionNote
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAttributeKey
from app.schemas.typings.knowledge.strings import KnowledgeAttributeValue
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey
from app.schemas.typings.profiles.strings import (
    CancellationPolicyText,
    ForbiddenRuleText,
    HandoffRuleText,
    ProfileAnswerText,
    ToneText,
)
from tests.assembly.builders import build_business, build_menu_item, interval
from tests.assembly.testbed import AssemblyTestbed


def seed_georgian_restaurant(
    testbed: AssemblyTestbed,
    plan_key: PlanKey = PlanKey.VOICE_AND_CHAT,
) -> BusinessDocument:
    """Tbilisi restaurant: ka, ru, en; GEL prices; a terrace with its own hours."""

    business = build_business(
        testbed,
        name="Café Rustaveli",
        niche_key=NicheKey.RESTAURANT,
        country_code="GE",
        city="Tbilisi",
        timezone_name="Asia/Tbilisi",
        currency_code="GEL",
        languages=["ka", "ru", "en"],
        plan_key=plan_key,
    )
    terrace = ResourceDocument(
        business_id=business.id,
        kind=ResourceKind.TABLE,
        name=ResourceName("Terrace"),
        capacity=ResourceCapacity(8),
        slot_minutes=SlotDurationMinutes(120),
        schedule=[interval(Weekday.SATURDAY, "12:00", "22:00")],
    )
    table = ResourceDocument(
        business_id=business.id,
        kind=ResourceKind.TABLE,
        name=ResourceName("Table 4"),
        capacity=ResourceCapacity(4),
        unit_count=ResourceUnitCount(3),
    )
    broken_table = ResourceDocument(
        business_id=business.id,
        kind=ResourceKind.TABLE,
        name=ResourceName("Broken table"),
        capacity=ResourceCapacity(2),
        is_active=False,
    )
    for resource in (terrace, table, broken_table):
        testbed.resource_repo.save(resource)

    testbed.profile_repo.save(
        BusinessProfileDocument(
            business_id=business.id,
            niche_key=NicheKey.RESTAURANT,
            answers_language=LanguageTag("ka"),
            address=BusinessAddress(
                text=AddressText("Rustaveli Ave 10, Tbilisi"),
                maps_url=WebLink("https://maps.example.com/rustaveli-10"),
            ),
            hours=[
                *(
                    interval(weekday, "12:00", "23:00")
                    for weekday in (
                        Weekday.MONDAY,
                        Weekday.TUESDAY,
                        Weekday.WEDNESDAY,
                        Weekday.THURSDAY,
                    )
                ),
                interval(Weekday.FRIDAY, "18:00", "24:00"),
                interval(Weekday.FRIDAY, "12:00", "15:00"),
                interval(Weekday.SATURDAY, "10:00", "24:00"),
            ],
            contacts=BusinessContacts(
                public_phone_number=E164PhoneNumber("+995322123456"),
                handoff_phone_number=E164PhoneNumber("+995555123456"),
            ),
            booking_rules=BookingRules(
                resource_kind=ResourceKind.TABLE,
                slot_minutes=SlotDurationMinutes(90),
                max_party_size=PartySize(12),
                min_notice_minutes=MinNoticeMinutes(60),
                deposit_minor=MoneyAmountMinor(5000),
                cancellation_policy=CancellationPolicyText("Free up to 2 hours before"),
            ),
            handoff_rules=[
                HandoffRuleText("банкет больше 20 человек"),
                HandoffRuleText("Allergy question"),
            ],
            forbidden=[
                ForbiddenRuleText("Discounts or special prices without approval"),
                ForbiddenRuleText("Не обещать парковку"),
            ],
            tone=ToneText("дружелюбно и коротко"),
            links=[
                BusinessLink(
                    kind=BusinessLinkKind.BOOKING_PAGE,
                    url=WebLink("https://example.ge/book"),
                ),
                BusinessLink(
                    kind=BusinessLinkKind.MENU,
                    url=WebLink("https://example.ge/menu"),
                ),
            ],
            niche_answers=[
                ProfileAnswer(
                    question_key=QuestionKey("cuisine"),
                    answer=ProfileAnswerText("georgian,european"),
                ),
                ProfileAnswer(
                    question_key=QuestionKey("live_music"),
                    answer=ProfileAnswerText("yes"),
                ),
                ProfileAnswer(
                    question_key=QuestionKey("banquet_manager_phone"),
                    answer=ProfileAnswerText("+995555123456"),
                ),
                ProfileAnswer(
                    question_key=QuestionKey("kids_menu"),
                    answer=ProfileAnswerText("  "),
                ),
                ProfileAnswer(
                    question_key=QuestionKey("retired_question"),
                    answer=ProfileAnswerText("stale answer"),
                ),
            ],
        )
    )
    khachapuri = build_menu_item(
        business,
        "Khachapuri Adjaruli",
        1800,
        body="Boat-shaped bread with cheese and egg",
        tags=["vegetarian"],
    )
    khachapuri.attributes = [
        KnowledgeAttribute(
            key=KnowledgeAttributeKey("portion_size"),
            value=KnowledgeAttributeValue("400 g"),
        )
    ]
    for item in (
        build_menu_item(business, "Mtsvadi", 2400),
        khachapuri,
        build_menu_item(
            business,
            "Is there parking?",
            None,
            kind=KnowledgeItemKind.FAQ,
            body="Yes, free, in the yard",
        ),
        build_menu_item(business, "Old dish", 999, is_active=False),
    ):
        testbed.knowledge_repo.save(item)

    for exception in (
        ScheduleExceptionDocument(
            business_id=business.id,
            date=LocalDate("2026-09-01"),
            note=ScheduleExceptionNote("Past holiday"),
        ),
        ScheduleExceptionDocument(
            business_id=business.id,
            date=LocalDate("2027-01-07"),
            note=ScheduleExceptionNote("Orthodox Christmas"),
        ),
        ScheduleExceptionDocument(
            business_id=business.id,
            date=LocalDate("2026-12-31"),
            is_closed_all_day=False,
            special_hours=[interval(Weekday.THURSDAY, "12:00", "18:00")],
            note=ScheduleExceptionNote("New Year's Eve"),
        ),
        ScheduleExceptionDocument(
            business_id=business.id,
            resource_id=terrace.id,
            date=LocalDate("2026-11-01"),
        ),
        ScheduleExceptionDocument(
            business_id=business.id,
            resource_id=broken_table.id,
            date=LocalDate("2026-11-02"),
        ),
    ):
        testbed.exception_repo.save(exception)

    return business
