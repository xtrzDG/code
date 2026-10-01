"""Businesses from several countries, seeded into a testbed.

Georgia (GEL, Georgian script), Italy (EUR), Japan (JPY without minor
units), Israel (ILS, Hebrew and Arabic written right to left) and an online
shop in the United States that takes orders instead of bookings.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import BillingPeriod, PlanKey, SubscriptionStatus
from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.businesses import BusinessLinkKind, Weekday
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import (
    BusinessDocument,
    BusinessMember,
    ManagerContact,
)
from app.schemas.domain.compliance import DpaAcceptanceDocument
from app.schemas.domain.knowledge import KnowledgeAttribute, KnowledgeItemDocument
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessAddress,
    BusinessContacts,
    BusinessLink,
    BusinessProfileDocument,
    OpeningInterval,
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
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.strings import AddressText, BusinessName, CityName
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.knowledge.constrained_integers import ServiceDurationMinutes
from app.schemas.typings.knowledge.constrained_strings import (
    KnowledgeAttributeKey,
    KnowledgeTag,
)
from app.schemas.typings.knowledge.strings import (
    KnowledgeAttributeValue,
    KnowledgeBody,
    KnowledgeTitle,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey
from app.schemas.typings.profiles.strings import (
    CancellationPolicyText,
    ForbiddenRuleText,
    HandoffRuleText,
    ProfileAnswerText,
    ToneText,
)
from tests.assembly.testbed import AssemblyTestbed


def interval(weekday: Weekday, opens: str, closes: str) -> OpeningInterval:
    """Interval from "HH:MM" texts; "24:00" closes at midnight."""

    open_hours, open_minutes = (int(part) for part in opens.split(":"))
    close_hours, close_minutes = (int(part) for part in closes.split(":"))
    return OpeningInterval(
        weekday=weekday,
        opens_at=OpeningMinuteOfDay(open_hours * 60 + open_minutes),
        closes_at=ClosingMinuteOfDay(close_hours * 60 + close_minutes),
    )


TRIAL_SECONDS: int = 14 * 24 * 60 * 60


def build_business(
    testbed: AssemblyTestbed,
    *,
    name: str,
    niche_key: NicheKey,
    country_code: str,
    city: str | None,
    timezone_name: str,
    currency_code: str,
    languages: list[str],
    plan_key: PlanKey = PlanKey.CHAT,
    is_launch_ready: bool = True,
) -> BusinessDocument:
    """
    A business with its owner and a staff member. A launch-ready one also
    has a manager contact, a running trial and the current DPA accepted,
    so only its profile and versions decide whether it may go live.
    """

    business = BusinessDocument(
        name=BusinessName(name),
        niche_key=niche_key,
        country_code=CountryCode(country_code),
        city=CityName(city) if city is not None else None,
        timezone=TimezoneName(timezone_name),
        currency_code=CurrencyCode(currency_code),
        languages=[LanguageTag(tag) for tag in languages],
        default_language=LanguageTag(languages[0]),
        owner_language=LanguageTag(languages[0]),
        plan_key=plan_key,
        data_region=DataRegion.EU,
        members=[
            BusinessMember(user_id=testbed.owner_id, role=BusinessMemberRole.OWNER),
            BusinessMember(user_id=testbed.staff_id, role=BusinessMemberRole.STAFF),
        ],
    )
    testbed.business_repo.save(business)
    if is_launch_ready:
        make_launch_ready(testbed, business)

    return business


def make_launch_ready(testbed: AssemblyTestbed, business: BusinessDocument) -> None:
    """A manager contact, a running trial and the current DPA accepted."""

    now = testbed.wall_clock.now_unix()
    business.manager_contacts = [
        ManagerContact(
            name=ManagerName("Nino"),
            channel=ManagerContactChannel.TELEGRAM,
            address=ManagerContactAddress("70001"),
            language=business.owner_language,
        )
    ]
    testbed.business_repo.save(business)
    testbed.subscription_repo.save(
        SubscriptionDocument(
            business_id=business.id,
            plan_key=business.plan_key,
            billing_period=BillingPeriod.MONTHLY,
            price_minor=MoneyAmountMinor(0),
            currency_code=business.currency_code,
            status=SubscriptionStatus.TRIALING,
            trial_ends_at=Microseconds(int(now) + TRIAL_SECONDS * 1_000_000),
            period_start=now,
            period_end=Microseconds(int(now) + TRIAL_SECONDS * 1_000_000),
            created_at=now,
            updated_at=now,
        )
    )
    testbed.dpa_repo.save(
        DpaAcceptanceDocument(
            business_id=business.id,
            document_version=testbed.settings.dpa_document_version,
            accepted_by=testbed.owner_id,
            accepted_at=now,
            created_at=now,
            updated_at=now,
        )
    )


def build_menu_item(
    business: BusinessDocument,
    title: str,
    price_minor: int | None,
    *,
    kind: KnowledgeItemKind = KnowledgeItemKind.MENU_ITEM,
    body: str | None = None,
    tags: list[str] | None = None,
    currency_code: str | None = None,
    duration_minutes: int | None = None,
    is_active: bool = True,
) -> KnowledgeItemDocument:
    return KnowledgeItemDocument(
        business_id=business.id,
        kind=kind,
        title=KnowledgeTitle(title),
        body=KnowledgeBody(body) if body is not None else None,
        price_minor=MoneyAmountMinor(price_minor) if price_minor is not None else None,
        currency_code=CurrencyCode(currency_code) if currency_code else None,
        duration_minutes=(
            ServiceDurationMinutes(duration_minutes)
            if duration_minutes is not None
            else None
        ),
        tags=[KnowledgeTag(tag) for tag in tags or []],
        is_active=is_active,
    )


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


def seed_italian_restaurant(
    testbed: AssemblyTestbed,
    is_launch_ready: bool = True,
) -> BusinessDocument:
    """Milan trattoria: it, en; prices in euros with cents."""

    business = build_business(
        testbed,
        is_launch_ready=is_launch_ready,
        name="Trattoria Milano",
        niche_key=NicheKey.RESTAURANT,
        country_code="IT",
        city="Milano",
        timezone_name="Europe/Rome",
        currency_code="EUR",
        languages=["it", "en"],
    )
    testbed.resource_repo.save(
        ResourceDocument(
            business_id=business.id,
            kind=ResourceKind.TABLE,
            name=ResourceName("Tavolo 1"),
            capacity=ResourceCapacity(6),
        )
    )
    testbed.profile_repo.save(
        BusinessProfileDocument(
            business_id=business.id,
            niche_key=NicheKey.RESTAURANT,
            answers_language=LanguageTag("it"),
            address=BusinessAddress(text=AddressText("Via Torino 5, Milano")),
            hours=[interval(Weekday.TUESDAY, "19:00", "23:30")],
            contacts=BusinessContacts(
                public_phone_number=E164PhoneNumber("+390212345678")
            ),
            booking_rules=BookingRules(
                resource_kind=ResourceKind.TABLE,
                slot_minutes=SlotDurationMinutes(120),
                max_party_size=PartySize(1),
            ),
        )
    )
    for item in (
        build_menu_item(business, "Pizza Margherita", 850),
        build_menu_item(business, "Tiramisù", 600, tags=["dessert"]),
    ):
        testbed.knowledge_repo.save(item)

    return business


def seed_japanese_restaurant(testbed: AssemblyTestbed) -> BusinessDocument:
    """Tokyo sushi bar: ja, en; yen have no minor units."""

    business = build_business(
        testbed,
        name="Sakura Sushi",
        niche_key=NicheKey.RESTAURANT,
        country_code="JP",
        city="Tokyo",
        timezone_name="Asia/Tokyo",
        currency_code="JPY",
        languages=["ja", "en"],
    )
    testbed.resource_repo.save(
        ResourceDocument(
            business_id=business.id,
            kind=ResourceKind.TABLE,
            name=ResourceName("カウンター"),
            capacity=ResourceCapacity(10),
        )
    )
    testbed.profile_repo.save(
        BusinessProfileDocument(
            business_id=business.id,
            niche_key=NicheKey.RESTAURANT,
            answers_language=LanguageTag("ja"),
            address=BusinessAddress(text=AddressText("東京都中央区銀座1-2-3")),
            hours=[interval(Weekday.WEDNESDAY, "17:00", "22:00")],
            booking_rules=BookingRules(
                resource_kind=ResourceKind.TABLE,
                slot_minutes=SlotDurationMinutes(60),
                max_party_size=PartySize(6),
                deposit_minor=MoneyAmountMinor(1000),
            ),
        )
    )
    testbed.knowledge_repo.save(build_menu_item(business, "にぎり盛り合わせ", 1500))
    return business


def seed_israeli_clinic(testbed: AssemblyTestbed) -> BusinessDocument:
    """Tel Aviv clinic: he, ar (both right to left), en; ILS prices."""

    business = build_business(
        testbed,
        name="מרפאת השרון",
        niche_key=NicheKey.CLINIC,
        country_code="IL",
        city="Tel Aviv",
        timezone_name="Asia/Jerusalem",
        currency_code="ILS",
        languages=["he", "ar", "en"],
        plan_key=PlanKey.VOICE_AND_CHAT,
    )
    testbed.resource_repo.save(
        ResourceDocument(
            business_id=business.id,
            kind=ResourceKind.STAFF,
            name=ResourceName("ד״ר כהן"),
            capacity=ResourceCapacity(1),
            slot_minutes=SlotDurationMinutes(30),
        )
    )
    testbed.profile_repo.save(
        BusinessProfileDocument(
            business_id=business.id,
            niche_key=NicheKey.CLINIC,
            answers_language=LanguageTag("he"),
            address=BusinessAddress(text=AddressText("רחוב דיזנגוף 50, תל אביב")),
            hours=[interval(Weekday.SUNDAY, "08:00", "16:00")],
            contacts=BusinessContacts(
                public_phone_number=E164PhoneNumber("+97231234567")
            ),
            booking_rules=BookingRules(
                resource_kind=ResourceKind.STAFF,
                slot_minutes=SlotDurationMinutes(30),
                max_party_size=PartySize(2),
            ),
            handoff_rules=[HandoffRuleText("תלונה")],
        )
    )
    testbed.knowledge_repo.save(
        build_menu_item(
            business,
            "ייעוץ רופא",
            30000,
            kind=KnowledgeItemKind.SERVICE,
            duration_minutes=30,
        )
    )
    return business


def seed_online_shop(
    testbed: AssemblyTestbed,
    has_opening_hours: bool = True,
) -> BusinessDocument:
    """
    New York online shop: no resources, no booking rules, no links; order
    questions are answered on weekdays.
    """

    business = build_business(
        testbed,
        name="Brooklyn Beans",
        niche_key=NicheKey.ONLINE_SHOP,
        country_code="US",
        city=None,
        timezone_name="America/New_York",
        currency_code="USD",
        languages=["en"],
    )
    testbed.profile_repo.save(
        BusinessProfileDocument(
            business_id=business.id,
            niche_key=NicheKey.ONLINE_SHOP,
            answers_language=LanguageTag("en"),
            hours=[
                interval(weekday, "09:00", "18:00")
                for weekday in (Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY)
                if has_opening_hours
            ],
        )
    )
    testbed.knowledge_repo.save(
        build_menu_item(
            business,
            "Espresso beans 1 kg",
            2450,
            kind=KnowledgeItemKind.PRODUCT,
        )
    )
    return business
