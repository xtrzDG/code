"""
The customer card on storage (1140): the tag lookup (case-folded keys kept
by a trigger), the VIP and blocked filter columns, a plain save that keeps
the card, atomic card changes, and the history reads behind visits, the
timeline and the search; the same on in-memory and on Postgres.
"""

from collections.abc import Callable

import pytest
from typed_time_provider import Microseconds

from app.repositories.conversation_repositories import ContactRepository
from app.repositories.customer_history_repository import CustomerHistoryRepository
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactBlock, ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
)
from app.schemas.dto.customers.customer_records import CustomerPageFilter
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.constrained_strings import CustomerTag
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, ProviderCallId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.customers.customer_card import add_tags
from tests.storage.conftest import CollectionFactory

pytestmark = pytest.mark.usefixtures("platform_scope")

BUSINESS: BusinessId = BusinessId()
NOW: int = 1_790_000_000
PAGE = KeysetSlice(limit=KeysetReadLimit(10))


def contacts(collections: CollectionFactory) -> ContactRepository:
    return ContactRepository(collections(ContactDocument, "contacts"))


def seed(repo: ContactRepository, name: str, seen: int) -> ContactDocument:
    contact = ContactDocument(
        business_id=BUSINESS,
        name=ContactName(name),
        last_seen_at=Microseconds(seen),
    )
    repo.save(contact)
    return contact


def tagging(tag: str, actor: UserId) -> Callable[[ContactDocument], None]:
    def apply(contact: ContactDocument) -> None:
        add_tags(contact, [CustomerTag(tag)], actor, Microseconds(9))

    return apply


def names(rows: list[ContactDocument]) -> list[str]:
    return [str(row.name) for row in rows]


def test_the_list_pages_by_tag_vip_and_block(collections: CollectionFactory) -> None:
    repo = contacts(collections)
    giorgi, nino, ana = (
        seed(repo, name, seen)
        for name, seen in (("Giorgi", 1), ("Nino", 2), ("Ana", 3))
    )
    owner = UserId()
    repo.change_card(
        BUSINESS,
        giorgi.id,
        tagging("Regular", owner),
    )
    repo.change_card(
        BUSINESS,
        nino.id,
        tagging("regular", owner),
    )

    def vip(contact: ContactDocument) -> None:
        contact.is_vip = True

    def block(contact: ContactDocument) -> None:
        contact.block = ContactBlock(blocked_at=Microseconds(9), blocked_by=owner)

    repo.change_card(BUSINESS, nino.id, vip)
    repo.change_card(BUSINESS, ana.id, block)

    def page(**filters: object) -> list[str]:
        return names(
            repo.page_customers(
                BUSINESS, PAGE, CustomerPageFilter.model_validate(filters)
            )
        )

    assert page() == ["Ana", "Nino", "Giorgi"]
    assert page(tag="REGULAR") == ["Nino", "Giorgi"]
    assert page(tag="regular", vip_only=True) == ["Nino"]
    assert page(blocked_only=True) == ["Ana"]
    assert page(tag="wholesale") == []

    # Taking the tag off drops the lookup key too.
    repo.change_card(BUSINESS, giorgi.id, lambda contact: contact.tags.clear())
    assert page(tag="regular") == ["Nino"]


def test_a_plain_save_keeps_the_card_a_change_made(
    collections: CollectionFactory,
) -> None:
    repo = contacts(collections)
    stale = seed(repo, "Giorgi", 1)
    owner = UserId()
    repo.change_card(
        BUSINESS,
        stale.id,
        tagging("vip", owner),
    )

    stale.phone_number = E164PhoneNumber("+995577123456")
    repo.save(stale)

    stored = repo.get(BUSINESS, stale.id)
    assert stored is not None
    assert stored.phone_number == "+995577123456"
    assert [str(mark.tag) for mark in stored.tags] == ["vip"]
    assert names(
        repo.page_customers(BUSINESS, PAGE, CustomerPageFilter(tag=CustomerTag("VIP")))
    ) == ["Giorgi"]


def conversation(
    contact: ContactDocument, channel: ChannelKind, at: int
) -> ConversationDocument:
    return ConversationDocument(
        business_id=BUSINESS,
        contact_id=contact.id,
        assistant_version_id=AssistantVersionId(),
        channel=channel,
        channel_user_id=ChannelUserId(f"{contact.id}-{channel}"),
        last_message_at=Microseconds(at),
    )


def booking(
    contact: ContactDocument, starts_at: int, status: BookingStatus
) -> BookingDocument:
    return BookingDocument(
        business_id=BUSINESS,
        resource_id=ResourceId(),
        contact_id=contact.id,
        starts_at=BookingStartsAtUnixSeconds(starts_at),
        ends_at=BookingEndsAtUnixSeconds(starts_at + 3600),
        party_size=PartySize(2),
        status=status,
        source_channel=ChannelKind.TELEGRAM,
    )


def test_visits_calls_and_latest_records_of_customers(
    collections: CollectionFactory,
) -> None:
    repo = contacts(collections)
    conversations = collections(ConversationDocument, "conversations")
    bookings = collections(BookingDocument, "bookings")
    calls = collections(CallDocument, "calls")
    history = CustomerHistoryRepository(conversations, bookings, calls)
    giorgi, nino = seed(repo, "Giorgi", 1), seed(repo, "Nino", 2)
    chat = conversation(giorgi, ChannelKind.TELEGRAM, 10)
    phone = conversation(giorgi, ChannelKind.PHONE, 20)
    for talk in (chat, phone, conversation(nino, ChannelKind.WHATSAPP, 30)):
        conversations.upsert(str(talk.id), talk)
    visits = [
        booking(giorgi, NOW - 86_400 * days, status)
        for days, status in (
            (40, BookingStatus.COMPLETED),
            (3, BookingStatus.CONFIRMED),
            (2, BookingStatus.CANCELLED),
            (-5, BookingStatus.CONFIRMED),
        )
    ]
    for item in visits:
        bookings.upsert(str(item.id), item)
    call = CallDocument(
        business_id=BUSINESS,
        conversation_id=phone.id,
        from_phone_number=E164PhoneNumber("+995577123456"),
        to_phone_number=E164PhoneNumber("+995322123456"),
        started_at=Microseconds(15),
        provider_call_id=ProviderCallId("call-1"),
    )
    calls.upsert(str(call.id), call)

    counted = history.visits_for_contacts(
        BUSINESS, [giorgi.id, nino.id], Microseconds(NOW * 1_000_000)
    )
    found_calls = history.calls_of_conversations(BUSINESS, [phone.id, chat.id])
    latest_conversations = history.latest_conversations_of(
        BUSINESS, [giorgi.id], DocumentQueryLimit(1)
    )
    latest_bookings = history.latest_bookings_of(
        BUSINESS, [giorgi.id], DocumentQueryLimit(2)
    )

    assert int(counted[giorgi.id].visit_count) == 2
    assert counted[giorgi.id].last_visit_at == visits[1].starts_at * 1_000_000
    assert nino.id not in counted or int(counted[nino.id].visit_count) == 0
    assert [item.id for item in found_calls] == [call.id]
    assert [item.id for item in latest_conversations] == [phone.id]
    assert [item.id for item in latest_bookings] == [visits[3].id, visits[2].id]
