"""
"Studio Lindenblatt": a hair and beauty salon in Berlin Prenzlauer Berg,
on the chat plan, with three stylists as bookable staff. Shows the same
product in another country, currency and pair of languages.
"""

from functools import partial

from app.registries.demo.demo_clock import DemoClock
from app.registries.demo.demo_foundation_parts import (
    bookable,
    connected_channel,
    knowledge_item,
    opening_hours,
)
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.businesses import BusinessLinkKind, BusinessStatus, Weekday
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.demo import DemoBusinessKey
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import (
    BusinessDocument,
    BusinessMember,
    ManagerContact,
)
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessAddress,
    BusinessContacts,
    BusinessLink,
    BusinessProfileDocument,
    ProfileAnswer,
)
from app.schemas.dto.demo_data import (
    DemoAssistantVersionPlan,
    DemoBusinessFoundation,
    DemoChannelCredential,
    DemoFoundationRequest,
)
from app.schemas.typings.bookings.constrained_integers import (
    MinNoticeMinutes,
    PartySize,
    SlotDurationMinutes,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.strings import AddressText, BusinessName, CityName
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
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
    HandoffRuleText,
    ProfileAnswerText,
    ToneText,
)

SALON_NAME: str = "Studio Lindenblatt"
SALON_TIMEZONE: str = "Europe/Berlin"
SALON_SITE: str = "https://studio-lindenblatt.example"
LENA: str = "Lena – Haare & Farbe"
MEHMET: str = "Mehmet – Barber"
SOFIA: str = "Sofia – Nägel & Wimpern"
TUESDAY_TO_FRIDAY: tuple[Weekday, ...] = (
    Weekday.TUESDAY,
    Weekday.WEDNESDAY,
    Weekday.THURSDAY,
    Weekday.FRIDAY,
)
SERVICE = KnowledgeItemKind.SERVICE


def build_salon_foundation(request: DemoFoundationRequest) -> DemoBusinessFoundation:
    clock = DemoClock(request.now, TimezoneName(SALON_TIMEZONE))
    opened = clock.past(-33, "09:30")
    business = BusinessDocument(
        name=BusinessName(SALON_NAME),
        niche_key=NicheKey.BEAUTY_SALON,
        country_code=CountryCode("DE"),
        city=CityName("Berlin"),
        timezone=TimezoneName(SALON_TIMEZONE),
        currency_code=CurrencyCode("EUR"),
        languages=[LanguageTag("de"), LanguageTag("en")],
        default_language=LanguageTag("de"),
        owner_language=LanguageTag("de"),
        plan_key=PlanKey.CHAT,
        status=BusinessStatus.LIVE,
        data_region=DataRegion.EU,
        members=[
            BusinessMember(user_id=request.owner_id, role=BusinessMemberRole.OWNER)
        ],
        manager_contacts=[
            ManagerContact(
                name=ManagerName("Lena Schneider"),
                channel=ManagerContactChannel.EMAIL,
                address=ManagerContactAddress("lena@studio-lindenblatt.example"),
                language=LanguageTag("de"),
            )
        ],
        created_at=opened,
        updated_at=clock.past(-30, "18:00"),
    )
    hours = [
        *opening_hours(TUESDAY_TO_FRIDAY, "10:00", "20:00"),
        *opening_hours((Weekday.SATURDAY,), "10:00", "16:00"),
    ]
    item = partial(knowledge_item, business, since=opened)
    return DemoBusinessFoundation(
        key=DemoBusinessKey.BERLIN_SALON,
        business=business,
        profile=BusinessProfileDocument(
            business_id=business.id,
            niche_key=business.niche_key,
            answers_language=LanguageTag("de"),
            address=BusinessAddress(
                text=AddressText("Kastanienallee 54, 10119 Berlin"),
                maps_url=WebLink(f"{SALON_SITE}/anfahrt"),
            ),
            hours=hours,
            contacts=BusinessContacts(
                public_phone_number=E164PhoneNumber("+493044012345"),
                handoff_phone_number=E164PhoneNumber("+4917612345678"),
            ),
            booking_rules=BookingRules(
                resource_kind=ResourceKind.STAFF,
                slot_minutes=SlotDurationMinutes(30),
                max_party_size=PartySize(2),
                min_notice_minutes=MinNoticeMinutes(120),
                cancellation_policy=CancellationPolicyText(
                    "Kostenlose Stornierung bis 24 Stunden vorher, danach 50 % des "
                    "Preises."
                ),
            ),
            handoff_rules=[
                HandoffRuleText("Reklamationen nach einer Behandlung"),
                HandoffRuleText(
                    "Allergien gegen Haarfarbe — erst Verträglichkeitstest"
                ),
            ],
            tone=ToneText("Locker und freundlich, per du, kurz"),
            links=[
                BusinessLink(kind=BusinessLinkKind.WEBSITE, url=WebLink(SALON_SITE)),
                BusinessLink(
                    kind=BusinessLinkKind.MAP, url=WebLink(f"{SALON_SITE}/anfahrt")
                ),
            ],
            niche_answers=[
                answer("service_categories", "hair,nails,brows_lashes,barber"),
                answer(
                    "masters_and_services",
                    "Lena: Schnitt, Farbe, Balayage. Mehmet: Herrenschnitt, Bart. "
                    "Sofia: Maniküre, Wimpernlifting, Augenbrauen.",
                ),
                answer("product_brands", "Davines, OPI"),
                answer("break_between_appointments", "10"),
                answer("client_chooses_master", "yes"),
                answer(
                    "late_arrival_policy",
                    "Ab 15 Minuten Verspätung kürzen oder verschieben wir den Termin.",
                ),
            ],
            created_at=opened,
            updated_at=business.updated_at,
        ),
        knowledge_items=[
            item(
                SERVICE,
                "Damenhaarschnitt & Föhnen",
                price_minor=6500,
                duration_minutes=60,
            ),
            item(SERVICE, "Herrenhaarschnitt", price_minor=3500, duration_minutes=30),
            item(
                SERVICE, "Bartpflege & Nassrasur", price_minor=2500, duration_minutes=30
            ),
            item(
                SERVICE,
                "Balayage",
                price_minor=16000,
                duration_minutes=180,
                body="Inklusive Pflege und Föhnen; Preis für mittellanges Haar.",
            ),
            item(SERVICE, "Ansatzfarbe", price_minor=7000, duration_minutes=90),
            item(
                SERVICE, "Maniküre mit Shellac", price_minor=4200, duration_minutes=60
            ),
            item(SERVICE, "Wimpernlifting", price_minor=5500, duration_minutes=60),
            item(
                SERVICE,
                "Augenbrauen zupfen & färben",
                price_minor=2500,
                duration_minutes=30,
            ),
            item(
                KnowledgeItemKind.FAQ,
                "Kann ich mit Karte zahlen?",
                body="Ja: EC-Karte, Kreditkarte, Apple Pay und Google Pay.",
                source=KnowledgeItemSource.PROFILE,
            ),
            item(
                KnowledgeItemKind.FAQ,
                "Wie komme ich hin?",
                body="U2 Eberswalder Straße, 3 Minuten zu Fuß. Parken: nur "
                "Anwohnerparken in der Straße.",
                source=KnowledgeItemSource.PROFILE,
            ),
        ],
        resources=[
            bookable(
                business,
                ResourceKind.STAFF,
                LENA,
                1,
                opened,
                slot_minutes=30,
                schedule=hours,
            ),
            bookable(
                business,
                ResourceKind.STAFF,
                MEHMET,
                1,
                opened,
                slot_minutes=30,
                schedule=[
                    *opening_hours(TUESDAY_TO_FRIDAY, "12:00", "20:00"),
                    *opening_hours((Weekday.SATURDAY,), "10:00", "16:00"),
                ],
            ),
            bookable(
                business,
                ResourceKind.STAFF,
                SOFIA,
                1,
                opened,
                slot_minutes=30,
                schedule=opening_hours(
                    (
                        Weekday.WEDNESDAY,
                        Weekday.THURSDAY,
                        Weekday.FRIDAY,
                        Weekday.SATURDAY,
                    ),
                    "10:00",
                    "18:00",
                ),
            ),
        ],
        channels=[
            connected_channel(
                business, ChannelKind.INSTAGRAM, opened, "17841400000000001"
            ),
            connected_channel(
                business, ChannelKind.WHATSAPP, opened, "209876543210988"
            ),
            connected_channel(
                business, ChannelKind.WEB_CHAT, opened, accent_color="#8E5A9B"
            ),
        ],
        channel_credentials=[
            DemoChannelCredential(
                channel=ChannelKind.INSTAGRAM,
                secret=ChannelSecret("EAADEMO-instagram-page-token-not-real"),
            )
        ],
        assistant_versions=[
            DemoAssistantVersionPlan(
                status=AssistantVersionStatus.PUBLISHED,
                created_at=clock.past(-31, "17:10"),
                published_at=clock.past(-30, "09:00"),
            )
        ],
    )


def answer(key: str, text: str) -> ProfileAnswer:
    return ProfileAnswer(question_key=QuestionKey(key), answer=ProfileAnswerText(text))
