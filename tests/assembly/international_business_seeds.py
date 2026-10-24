"""
Businesses of other countries seeded into a testbed: Italy (EUR), Japan (JPY
without minor units), Israel (ILS, Hebrew and Arabic written right to left)
and an online shop in the United States that takes orders, not bookings.
"""

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.businesses import Weekday
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessAddress,
    BusinessContacts,
    BusinessProfileDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import (
    PartySize,
    ResourceCapacity,
    SlotDurationMinutes,
)
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.profiles.strings import HandoffRuleText
from tests.assembly.builders import build_business, build_menu_item, interval
from tests.assembly.testbed import AssemblyTestbed


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
