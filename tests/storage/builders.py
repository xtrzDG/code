"""Documents from businesses in several countries, languages and currencies."""

from dataclasses import dataclass

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import LlmTurnRole
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import (
    BusinessDocument,
    BusinessMember,
    ManagerContact,
)
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import LlmTurnDocument
from app.schemas.domain.knowledge import KnowledgeAttribute, KnowledgeItemDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.constrained_integers import (
    LlmTurnSequenceNumber,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    LlmProviderPayload,
)
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
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId


@dataclass(frozen=True)
class CountrySample:
    """A business setting from one country: language, money, time zone, phone."""

    business_name: str
    city: str
    country_code: str
    language: str
    currency_code: str
    timezone: str
    phone_number: str
    dish_title: str
    dish_body: str
    price_minor: int
    customer_name: str


COUNTRY_SAMPLES: tuple[CountrySample, ...] = (
    CountrySample(
        business_name="სასადილო „ძველი თბილისი“",
        city="თბილისი",
        country_code="GE",
        language="ka",
        currency_code="GEL",
        timezone="Asia/Tbilisi",
        phone_number="+995555123456",
        dish_title="ხაჭაპური აჭარული",
        dish_body="ყველი, კვერცხი და კარაქი — 18 ₾",
        price_minor=1800,
        customer_name="ნინო ბერიძე",
    ),
    CountrySample(
        business_name="מסעדת הים",
        city="תל אביב-יפו",
        country_code="IL",
        language="he",
        currency_code="ILS",
        timezone="Asia/Jerusalem",
        phone_number="+972501234567",
        dish_title="חומוס עם פול",
        dish_body="מוגש עם פיתה חמה ‎₪42",
        price_minor=4200,
        customer_name="נועה כהן",
    ),
    CountrySample(
        business_name="مطعم الخليج",
        city="دبي",
        country_code="AE",
        language="ar",
        currency_code="AED",
        timezone="Asia/Dubai",
        phone_number="+971501234567",
        dish_title="شاورما دجاج",
        dish_body="مع الثومية والمخلل ٣٥ د.إ",
        price_minor=3500,
        customer_name="ليلى حداد",
    ),
    CountrySample(
        business_name="らーめん 一番",
        city="東京",
        country_code="JP",
        language="ja",
        currency_code="JPY",
        timezone="Asia/Tokyo",
        phone_number="+81312345678",
        dish_title="醤油ラーメン 🍜",
        dish_body="チャーシュー付き ¥980",
        price_minor=980,
        customer_name="山田 花子",
    ),
    CountrySample(
        business_name="Churrascaria Gaúcha",
        city="São Paulo",
        country_code="BR",
        language="pt",
        currency_code="BRL",
        timezone="America/Sao_Paulo",
        phone_number="+5511912345678",
        dish_title="Picanha na brasa",
        dish_body='Acompanha farofa e "vinagrete" \\ R$ 89,90',
        price_minor=8990,
        customer_name="João Conceição",
    ),
    CountrySample(
        business_name="Кофейня «Алматы»",
        city="Алматы",
        country_code="KZ",
        language="kk",
        currency_code="KZT",
        timezone="Asia/Almaty",
        phone_number="+77011234567",
        dish_title="Бауырсақ",
        dish_body="Таңғы асқа\nжаңа піскен — 1 500 ₸",
        price_minor=150000,
        customer_name="Әлия Нұрланқызы",
    ),
)


def build_business(sample: CountrySample, owner_id: UserId) -> BusinessDocument:
    return BusinessDocument(
        name=BusinessName(sample.business_name),
        niche_key=NicheKey.RESTAURANT,
        country_code=CountryCode(sample.country_code),
        city=CityName(sample.city),
        timezone=TimezoneName(sample.timezone),
        currency_code=CurrencyCode(sample.currency_code),
        languages=[LanguageTag(sample.language), LanguageTag("en")],
        default_language=LanguageTag(sample.language),
        owner_language=LanguageTag(sample.language),
        plan_key=PlanKey.VOICE_AND_CHAT,
        data_region=DataRegion.EU,
        members=[BusinessMember(user_id=owner_id, role=BusinessMemberRole.OWNER)],
        manager_contacts=[
            ManagerContact(
                name=ManagerName(sample.customer_name),
                channel=ManagerContactChannel.WHATSAPP,
                address=ManagerContactAddress(sample.phone_number),
                language=LanguageTag(sample.language),
            )
        ],
    )


def build_owner(sample: CountrySample) -> UserDocument:
    return UserDocument(
        login_method=LoginMethod.PHONE,
        phone_number=E164PhoneNumber(sample.phone_number),
        country_code=CountryCode(sample.country_code),
        locale=LanguageTag(sample.language),
    )


def build_email_user(email: str, locale: str) -> UserDocument:
    return UserDocument(
        login_method=LoginMethod.EMAIL,
        email=EmailAddress(email),
        locale=LanguageTag(locale),
    )


def build_knowledge_item(
    sample: CountrySample,
    business_id: BusinessId,
) -> KnowledgeItemDocument:
    return KnowledgeItemDocument(
        business_id=business_id,
        kind=KnowledgeItemKind.MENU_ITEM,
        title=KnowledgeTitle(sample.dish_title),
        body=KnowledgeBody(sample.dish_body),
        price_minor=MoneyAmountMinor(sample.price_minor),
        currency_code=CurrencyCode(sample.currency_code),
        duration_minutes=ServiceDurationMinutes(15),
        tags=[KnowledgeTag("signature"), KnowledgeTag("gluten-free")],
        attributes=[
            KnowledgeAttribute(
                key=KnowledgeAttributeKey("spice_level"),
                value=KnowledgeAttributeValue("🌶️🌶️"),
            )
        ],
        languages=[LanguageTag(sample.language)],
    )


def build_contact(sample: CountrySample, business_id: BusinessId) -> ContactDocument:
    return ContactDocument(
        business_id=business_id,
        name=ContactName(sample.customer_name),
        phone_number=E164PhoneNumber(sample.phone_number),
        language=LanguageTag(sample.language),
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.WHATSAPP,
                channel_user_id=ChannelUserId(sample.phone_number.removeprefix("+")),
            )
        ],
    )


def build_llm_turn(
    conversation_id: ConversationId,
    sequence_number: int,
    text: str,
) -> LlmTurnDocument:
    payload: str = (
        '{"role": "user", "content": [{"type": "text", "text": '
        f'"{text}"'
        '}], "meta": {"escaped": "line\\nbreak \\"quoted\\" \\\\ \\u2028"}}'
    )
    return LlmTurnDocument(
        conversation_id=conversation_id,
        sequence_number=LlmTurnSequenceNumber(sequence_number),
        role=LlmTurnRole.USER,
        payload=LlmProviderPayload(payload),
    )
