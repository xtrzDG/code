"""
"Mtsvane Ezo" (მწვანე ეზო, "green courtyard"): a Georgian restaurant in Old
Tbilisi, live for six weeks, owned by the demo owner with a hall manager
on staff. Guests write in Georgian, Russian and English, and tourists
from Israel and the Arab countries in Hebrew and Arabic.
"""

from app.registries.demo.demo_clock import DemoClock
from app.registries.demo.demo_foundation_parts import (
    DEMO_STAFF_TEMPLATES,
    bookable,
    connected_channel,
    opening_hours,
)
from app.registries.demo.tbilisi_restaurant.restaurant_menu import (
    build_restaurant_knowledge,
)
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.businesses import BusinessLinkKind, BusinessStatus, Weekday
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.demo import DemoBusinessKey
from app.schemas.constants.handoffs import ManagerContactChannel
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
    OpeningInterval,
    ProfileAnswer,
)
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.dto.demo_data import (
    DemoAssistantVersionPlan,
    DemoBusinessFoundation,
    DemoChannelCredential,
    DemoFoundationRequest,
)
from app.schemas.typings.assistants.constrained_floats import AverageJudgeScore
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.bookings.constrained_integers import (
    MinNoticeMinutes,
    PartySize,
    SlotDurationMinutes,
)
from app.schemas.typings.bookings.strings import ScheduleExceptionNote
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.strings import AddressText, BusinessName, CityName
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.handoffs.constrained_strings import ManagerTelegramUsername
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
    ForbiddenRuleText,
    HandoffRuleText,
    ProfileAnswerText,
    ToneText,
)

RESTAURANT_NAME: str = "Mtsvane Ezo"
RESTAURANT_TIMEZONE: str = "Asia/Tbilisi"
# The assistant's phone line (calls forwarded on no answer).
RESTAURANT_ASSISTANT_LINE: str = "+995322190020"
# The restaurant's own number: guests call it (unanswered calls go to the
# assistant line) and write to it on WhatsApp Business.
RESTAURANT_PUBLIC_NUMBER: str = "+995322190019"
SITE: str = "https://mtsvane-ezo.example"
WINDOW_TABLE: str = "Стол у окна (2 гостя)"
HALL_TABLE: str = "Стол в зале (4 гостя)"
COURTYARD_TABLE: str = "Стол во дворе (6 гостей)"
LONG_TABLE: str = "Большой стол (10 гостей)"
WEEKDAYS: tuple[Weekday, ...] = (
    Weekday.MONDAY,
    Weekday.TUESDAY,
    Weekday.WEDNESDAY,
    Weekday.THURSDAY,
)


def build_restaurant_foundation(
    request: DemoFoundationRequest,
) -> DemoBusinessFoundation:
    clock = DemoClock(request.now, TimezoneName(RESTAURANT_TIMEZONE))
    opened = clock.past(-48, "11:20")
    business = BusinessDocument(
        name=BusinessName(RESTAURANT_NAME),
        niche_key=NicheKey.RESTAURANT,
        country_code=CountryCode("GE"),
        city=CityName("Tbilisi"),
        timezone=TimezoneName(RESTAURANT_TIMEZONE),
        currency_code=CurrencyCode("GEL"),
        languages=[LanguageTag(tag) for tag in ("ka", "ru", "en")],
        default_language=LanguageTag("ka"),
        owner_language=LanguageTag("ru"),
        plan_key=PlanKey.VOICE_AND_CHAT,
        status=BusinessStatus.LIVE,
        data_region=DataRegion.EU,
        members=[
            BusinessMember(user_id=request.owner_id, role=BusinessMemberRole.OWNER),
            BusinessMember(user_id=request.staff_id, role=BusinessMemberRole.STAFF),
        ],
        manager_contacts=[
            ManagerContact(
                name=ManagerName("Тамар, администратор зала"),
                channel=ManagerContactChannel.TELEGRAM,
                address=ManagerContactAddress("700100200"),
                language=LanguageTag("ru"),
                telegram_username=ManagerTelegramUsername("tamar_mtsvane"),
            ),
            ManagerContact(
                name=ManagerName("გიორგი, შეფ-მზარეული"),
                channel=ManagerContactChannel.WHATSAPP,
                address=ManagerContactAddress("+995599102030"),
                language=LanguageTag("ka"),
            ),
        ],
        created_at=opened,
        updated_at=clock.past(-20, "10:05"),
    )
    hours: list[OpeningInterval] = [
        *opening_hours(WEEKDAYS, "12:00", "23:00"),
        *opening_hours((Weekday.FRIDAY, Weekday.SATURDAY), "12:00", "24:00"),
        *opening_hours((Weekday.SUNDAY,), "12:00", "22:00"),
    ]
    resources = [
        bookable(business, ResourceKind.TABLE, WINDOW_TABLE, 2, opened, unit_count=4),
        bookable(business, ResourceKind.TABLE, HALL_TABLE, 4, opened, unit_count=6),
        bookable(
            business, ResourceKind.TABLE, COURTYARD_TABLE, 6, opened, unit_count=3
        ),
        bookable(business, ResourceKind.TABLE, LONG_TABLE, 10, opened),
    ]
    channels = [
        connected_channel(business, ChannelKind.TELEGRAM, opened, "mtsvane_ezo_bot"),
        connected_channel(
            business,
            ChannelKind.WHATSAPP,
            opened,
            "109876543210987",
            staff_templates=DEMO_STAFF_TEMPLATES,
            # WhatsApp Business on the restaurant's own number.
            whatsapp_number=RESTAURANT_PUBLIC_NUMBER.removeprefix("+"),
        ),
        connected_channel(
            business, ChannelKind.WEB_CHAT, opened, accent_color="#2F7D4F"
        ),
        connected_channel(
            business, ChannelKind.PHONE, opened, RESTAURANT_ASSISTANT_LINE
        ),
    ]
    return DemoBusinessFoundation(
        key=DemoBusinessKey.TBILISI_RESTAURANT,
        business=business,
        profile=build_restaurant_profile(business, hours),
        knowledge_items=build_restaurant_knowledge(business, opened),
        resources=resources,
        schedule_exceptions=[
            ScheduleExceptionDocument(
                business_id=business.id,
                date=clock.date(9),
                note=ScheduleExceptionNote("Санитарный день, ресторан закрыт"),
                created_at=clock.past(-3, "16:40"),
                updated_at=clock.past(-3, "16:40"),
            ),
            ScheduleExceptionDocument(
                business_id=business.id,
                date=clock.date(6),
                is_closed_all_day=False,
                special_hours=opening_hours(
                    (Weekday(clock.weekday_index(clock.at(6, "12:00")) + 1),),
                    "12:00",
                    "17:00",
                ),
                note=ScheduleExceptionNote("Вечером закрытое мероприятие"),
                created_at=clock.past(-2, "11:15"),
                updated_at=clock.past(-2, "11:15"),
            ),
        ],
        channels=channels,
        channel_credentials=[
            DemoChannelCredential(
                channel=ChannelKind.TELEGRAM,
                secret=ChannelSecret("7000000001:AAF-demo-bot-token-not-real-000000"),
            )
        ],
        assistant_versions=[
            DemoAssistantVersionPlan(
                status=AssistantVersionStatus.ARCHIVED,
                created_at=clock.past(-46, "15:30"),
                published_at=clock.past(-45, "10:10"),
                test_score=AverageJudgeScore(4.4),
            ),
            DemoAssistantVersionPlan(
                status=AssistantVersionStatus.PUBLISHED,
                created_at=clock.past(-20, "10:20"),
                published_at=clock.past(-19, "09:45"),
                voice_agent_id=VoiceAgentId("agent_demo_mtsvane_ezo_v2"),
            ),
            DemoAssistantVersionPlan(
                status=AssistantVersionStatus.DRAFT,
                created_at=clock.ago(hours=20),
            ),
        ],
    )


def build_restaurant_profile(
    business: BusinessDocument, hours: list[OpeningInterval]
) -> BusinessProfileDocument:
    def answer(key: str, text: str) -> ProfileAnswer:
        return ProfileAnswer(
            question_key=QuestionKey(key), answer=ProfileAnswerText(text)
        )

    return BusinessProfileDocument(
        business_id=business.id,
        niche_key=business.niche_key,
        answers_language=LanguageTag("ru"),
        address=BusinessAddress(
            text=AddressText("Тбилиси, ул. Котэ Абхази, 27 (Старый город)"),
            maps_url=WebLink(f"{SITE}/map"),
        ),
        hours=hours,
        contacts=BusinessContacts(
            public_phone_number=E164PhoneNumber(RESTAURANT_PUBLIC_NUMBER),
            handoff_phone_number=E164PhoneNumber("+995599102030"),
        ),
        booking_rules=BookingRules(
            resource_kind=ResourceKind.TABLE,
            slot_minutes=SlotDurationMinutes(120),
            max_party_size=PartySize(10),
            min_notice_minutes=MinNoticeMinutes(60),
            cancellation_policy=CancellationPolicyText(
                "Бесплатная отмена за 3 часа до визита. Для компаний от 8 гостей — "
                "предоплата 20 %."
            ),
        ),
        handoff_rules=[
            HandoffRuleText("Банкеты и компании больше 10 гостей"),
            HandoffRuleText("Жалобы на блюда или обслуживание"),
            HandoffRuleText("Аллергии и особые диеты — уточнить у шефа"),
        ],
        forbidden=[
            ForbiddenRuleText("Обещать стол во дворе в дождь"),
            ForbiddenRuleText("Называть цену банкета без менеджера"),
        ],
        tone=ToneText(
            "Тепло и по-домашнему, коротко, на «вы»; не больше одного эмодзи"
        ),
        links=[
            BusinessLink(kind=BusinessLinkKind.MENU, url=WebLink(f"{SITE}/menu")),
            BusinessLink(kind=BusinessLinkKind.MAP, url=WebLink(f"{SITE}/map")),
            BusinessLink(
                kind=BusinessLinkKind.DELIVERY, url=WebLink(f"{SITE}/delivery")
            ),
            BusinessLink(kind=BusinessLinkKind.WEBSITE, url=WebLink(SITE)),
        ],
        google_review_url=WebLink(f"{SITE}/review"),
        niche_answers=[
            answer("cuisine", "Грузинская домашняя кухня и вино из Кахети"),
            answer("seating_capacity", "64"),
            answer("banquets", "separate_hall"),
            answer("banquet_max_guests", "45"),
            answer("delivery", "delivery_apps"),
            answer(
                "live_music",
                "По пятницам и субботам с 20:00: гитара и грузинское многоголосие",
            ),
            answer("kids_menu", "yes"),
            answer("outdoor_seating", "yes"),
            answer("dietary_options", "vegetarian,vegan"),
            answer(
                "allergen_policy",
                "Грецкий орех есть во многих блюдах (пхали, бадриджани, чурчхела). "
                "При аллергии предупредите при брони — шеф приготовит без орехов.",
            ),
        ],
        created_at=business.created_at,
        updated_at=business.updated_at,
    )
