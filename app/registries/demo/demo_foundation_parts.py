"""Building blocks of the demo businesses' foundations."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.businesses import Weekday
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import (
    ChannelDocument,
    ChannelPublicProfile,
    WebChatAppearance,
    WhatsAppStaffTemplate,
)
from app.schemas.domain.knowledge import KnowledgeAttribute, KnowledgeItemDocument
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import (
    ResourceCapacity,
    ResourceUnitCount,
    SlotDurationMinutes,
)
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
    WidgetAccentColor,
)
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.knowledge.constrained_integers import (
    BufferMinutes,
    ServiceDurationMinutes,
)
from app.schemas.typings.knowledge.constrained_strings import (
    KnowledgeAttributeKey,
    KnowledgeTag,
)
from app.schemas.typings.knowledge.strings import (
    KnowledgeAttributeValue,
    KnowledgeBody,
    KnowledgeTitle,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.sharing.constrained_strings import (
    InstagramUsername,
    WhatsAppNumberDigits,
)

MINUTES_PER_HOUR: int = 60


def minute_of_day(clock: str) -> int:
    """ "19:30" -> 1170; "24:00" is the end of the day."""

    hours, minutes = (int(part) for part in clock.split(":"))
    return hours * MINUTES_PER_HOUR + minutes


def opening_hours(
    days: Sequence[Weekday], opens: str, closes: str
) -> list[OpeningInterval]:
    """The same hours on each of `days`."""

    return [
        OpeningInterval(
            weekday=day,
            opens_at=OpeningMinuteOfDay(minute_of_day(opens)),
            closes_at=ClosingMinuteOfDay(minute_of_day(closes)),
        )
        for day in days
    ]


def connected_channel(
    business: BusinessDocument,
    kind: ChannelKind,
    since: Microseconds,
    external_id: str | None = None,
    accent_color: str | None = None,
    staff_template: tuple[str, str] | None = None,
    whatsapp_number: str | None = None,
    instagram_username: str | None = None,
) -> ChannelDocument:
    """
    `staff_template`: the WhatsApp template name and its language;
    `whatsapp_number` (digits) and `instagram_username`: the address
    customers open a chat with, which a real connection learns from Meta,
    so the share links can offer the channel.
    """
    return ChannelDocument(
        business_id=business.id,
        kind=kind,
        external_id=None if external_id is None else ChannelExternalId(external_id),
        status=ChannelStatus.CONNECTED,
        web_chat_appearance=(
            None
            if accent_color is None
            else WebChatAppearance(accent_color=WidgetAccentColor(accent_color))
        ),
        whatsapp_staff_template=(
            None
            if staff_template is None
            else WhatsAppStaffTemplate(
                name=WhatsAppTemplateName(staff_template[0]),
                language_code=WhatsAppTemplateLanguageCode(staff_template[1]),
            )
        ),
        public_profile=(
            None
            if whatsapp_number is None and instagram_username is None
            else ChannelPublicProfile(
                whatsapp_number=(
                    None
                    if whatsapp_number is None
                    else WhatsAppNumberDigits(whatsapp_number)
                ),
                instagram_username=(
                    None
                    if instagram_username is None
                    else InstagramUsername(instagram_username)
                ),
            )
        ),
        created_at=since,
        updated_at=since,
    )


def knowledge_item(
    business: BusinessDocument,
    kind: KnowledgeItemKind,
    title: str,
    since: Microseconds,
    body: str | None = None,
    price_minor: int | None = None,
    duration_minutes: int | None = None,
    buffer_minutes: int | None = None,
    tags: Sequence[str] = (),
    attributes: Sequence[tuple[str, str]] = (),
    source: KnowledgeItemSource = KnowledgeItemSource.OWNER,
    is_active: bool = True,
) -> KnowledgeItemDocument:
    return KnowledgeItemDocument(
        business_id=business.id,
        kind=kind,
        title=KnowledgeTitle(title),
        body=None if body is None else KnowledgeBody(body),
        price_minor=None if price_minor is None else MoneyAmountMinor(price_minor),
        currency_code=None if price_minor is None else business.currency_code,
        duration_minutes=(
            None
            if duration_minutes is None
            else ServiceDurationMinutes(duration_minutes)
        ),
        buffer_minutes=(
            None if buffer_minutes is None else BufferMinutes(buffer_minutes)
        ),
        tags=[KnowledgeTag(tag) for tag in tags],
        attributes=[
            KnowledgeAttribute(
                key=KnowledgeAttributeKey(key), value=KnowledgeAttributeValue(value)
            )
            for key, value in attributes
        ],
        languages=[LanguageTag(str(business.owner_language))],
        source=source,
        is_active=is_active,
        created_at=since,
        updated_at=since,
    )


def bookable(
    business: BusinessDocument,
    kind: ResourceKind,
    name: str,
    capacity: int,
    since: Microseconds,
    unit_count: int = 1,
    slot_minutes: int | None = None,
    schedule: Sequence[OpeningInterval] = (),
    serves: Sequence[KnowledgeItemDocument] = (),
) -> ResourceDocument:
    """`serves`: the services this resource performs (none: any of its unit)."""

    return ResourceDocument(
        business_id=business.id,
        kind=kind,
        name=ResourceName(name),
        capacity=ResourceCapacity(capacity),
        unit_count=ResourceUnitCount(unit_count),
        booking_unit=BookingUnit.TIME_SLOT,
        slot_minutes=None
        if slot_minutes is None
        else SlotDurationMinutes(slot_minutes),
        schedule=list(schedule),
        serves_item_ids=[item.id for item in serves],
        created_at=since,
        updated_at=since,
    )
