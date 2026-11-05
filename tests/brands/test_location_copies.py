"""
"New location from…" copies the profile, resources, knowledge and channel
settings under new ids, keeps the links between them, and leaves behind
everything that belongs to the source: its address, numbers and review
page, calendar links, answer corrections and channel accounts.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.channels import WebChatAppearance
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import (
    BusinessAddress,
    BusinessContacts,
    BusinessProfileDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.brands.location_templates import (
    ChannelSettingsTemplate,
    LocationTemplate,
)
from app.schemas.typings.bookings.constrained_integers import ResourceCapacity
from app.schemas.typings.bookings.strings import ExternalCalendarId, ResourceName
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.channels.constrained_strings import WidgetAccentColor
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.utilities.brands.location_copies import copy_location

SOURCE = BusinessId()
TARGET = BusinessId()
NOW = Microseconds(1_800_000_000_000_000)


def template() -> LocationTemplate:
    item = KnowledgeItemDocument(
        business_id=SOURCE,
        kind=KnowledgeItemKind.SERVICE,
        title=KnowledgeTitle("Tasting menu"),
        correction_of=MessageId(),
    )
    table = ResourceDocument(
        business_id=SOURCE,
        kind=ResourceKind.TABLE,
        name=ResourceName("Window table"),
        capacity=ResourceCapacity(4),
        serves_item_ids=[item.id],
        external_calendar_id=ExternalCalendarId("vera@group.calendar.google.com"),
    )
    performer = item.model_copy(update={"performer_resource_ids": [table.id]})
    return LocationTemplate(
        profile=BusinessProfileDocument(
            business_id=SOURCE,
            niche_key=NicheKey.RESTAURANT,
            answers_language=LanguageTag("ka"),
            address=BusinessAddress(text=AddressText("Vera, Kostava St 1")),
            contacts=BusinessContacts(
                public_phone_number=E164PhoneNumber("+995322000111"),
                handoff_phone_number=E164PhoneNumber("+995599000111"),
            ),
            google_review_url=WebLink("https://g.page/r/vera-review"),
        ),
        resources=[table],
        knowledge_items=[performer],
        channels=[
            ChannelSettingsTemplate(
                kind=ChannelKind.WEB_CHAT,
                web_chat_appearance=WebChatAppearance(
                    accent_color=WidgetAccentColor("#ad5732")
                ),
            ),
            ChannelSettingsTemplate(kind=ChannelKind.TELEGRAM),
        ],
    )


def test_the_copies_belong_to_the_new_location_under_new_ids() -> None:
    source = template()

    copies = copy_location(source, TARGET, NOW)

    [table] = copies.resources
    [item] = copies.knowledge_items
    assert table.business_id == item.business_id == TARGET
    assert table.id != source.resources[0].id
    assert item.id != source.knowledge_items[0].id
    # The links between resources and items point at the copies.
    assert table.serves_item_ids == [item.id]
    assert item.performer_resource_ids == [table.id]
    assert copies.profile is not None and copies.profile.business_id == TARGET


def test_nothing_of_the_source_place_people_or_accounts_travels() -> None:
    copies = copy_location(template(), TARGET, NOW)

    profile = copies.profile
    assert profile is not None
    assert profile.address is None
    assert profile.google_review_url is None
    assert profile.contacts == BusinessContacts()
    assert copies.resources[0].external_calendar_id is None
    assert copies.knowledge_items[0].correction_of is None
    for channel in copies.channels:
        assert channel.business_id == TARGET
        assert channel.status is ChannelStatus.PENDING
        assert channel.external_id is None
        assert channel.encrypted_secret is None
        assert channel.public_profile is None
    web_chat = next(c for c in copies.channels if c.kind is ChannelKind.WEB_CHAT)
    assert web_chat.web_chat_appearance is not None
