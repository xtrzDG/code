"""Saved replies filled in for one conversation, in its language."""

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.inbox import QuickReplyVariable
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.inbox.quick_replies import (
    ConversationQuickRepliesQuery,
    FilledQuickReplyList,
)
from tests.inbox.inbox_builders import book, talk
from tests.inbox.inbox_world import InboxWorld
from tests.inbox.quick_reply_steps import reply_request, save

CONFIRM_VARIANTS: list[dict[str, str]] = [
    {"language": "en", "text": "See you at {booking_time}, {name}! {business_name}"},
    {"language": "ru", "text": "Ждём вас: {booking_time}. {name}, до встречи!"},
]


def fill(world: InboxWorld, conversation: ConversationDocument) -> FilledQuickReplyList:
    return world.fill_quick_replies().run(
        ConversationQuickRepliesQuery(
            user_id=world.staff.id,
            business_id=world.business.id,
            conversation_id=conversation.id,
        )
    )


def test_the_conversation_language_picks_the_variant_and_fills_it() -> None:
    world = InboxWorld()
    save(world, reply_request())
    conversation = talk(world, "Nino", minutes_ago=2, language="ka")

    filled = fill(world, conversation).items[0]

    assert str(filled.language) == "ka"
    assert str(filled.text) == "გამარჯობა, Nino! ღია ვართ 9:00-23:00."
    assert filled.missing_variables == []


def test_the_next_booking_is_written_in_the_business_time_zone() -> None:
    world = InboxWorld()
    save(world, reply_request("confirm", "Confirm", CONFIRM_VARIANTS))
    conversation = talk(world, "Nino", minutes_ago=2, language="en")
    book(world, conversation, starts_in_minutes=60 * 24, status=BookingStatus.CANCELLED)
    book(world, conversation, starts_in_minutes=60 * 5)
    book(world, conversation, starts_in_minutes=60 * 30)
    book(world, conversation, starts_in_minutes=-30)

    filled = fill(world, conversation).items[0]

    # 09:00 UTC + 5 hours is 18:00 in Tbilisi (UTC+4) the same day.
    assert str(filled.text) == (
        f"See you at Oct 3, 2026, 6:00 PM, Nino! {world.business.name}"
    )


def test_values_the_conversation_lacks_stay_for_staff_to_complete() -> None:
    world = InboxWorld()
    save(world, reply_request("confirm", "Confirm", CONFIRM_VARIANTS))
    conversation = talk(world, None, minutes_ago=2, language="ru")

    filled = fill(world, conversation).items[0]

    assert str(filled.language) == "ru"
    assert str(filled.text) == "Ждём вас: {booking_time}. {name}, до встречи!"
    assert filled.missing_variables == [
        QuickReplyVariable.BOOKING_TIME,
        QuickReplyVariable.NAME,
    ]


def test_a_language_without_a_variant_falls_back_to_the_business_language() -> None:
    world = InboxWorld()
    save(world, reply_request())
    german = talk(world, "Lena", minutes_ago=2, language="de")
    unknown = talk(world, "Sam", minutes_ago=1, language=None)
    save(
        world,
        reply_request("thanks", "Thanks", [{"language": "en", "text": "Thank you!"}]),
    )

    filled = {str(item.shortcut): item for item in fill(world, german).items}

    assert str(filled["hours"].language) == "ka"
    assert str(filled["thanks"].language) == "en"
    assert str(fill(world, unknown).items[0].language) == "ka"


def test_a_regional_language_uses_its_base_variant() -> None:
    world = InboxWorld()
    save(world, reply_request())
    conversation = talk(world, "Ivan", minutes_ago=2, language="ru-KZ")

    assert str(fill(world, conversation).items[0].language) == "ru"


def test_reading_the_customer_for_replies_is_audited() -> None:
    world = InboxWorld()
    save(world, reply_request())
    conversation = talk(world, "Nino", minutes_ago=2)

    fill(world, conversation)

    entry = world.audit_entries()[-1]
    assert (entry.action, str(entry.entity), str(entry.entity_id)) == (
        AuditAction.VIEW,
        "conversation",
        str(conversation.id),
    )
    assert entry.actor_id == world.staff.id


def test_a_business_without_replies_fills_none_and_audits_nothing() -> None:
    world = InboxWorld()
    conversation = talk(world, "Nino", minutes_ago=2)

    assert fill(world, conversation).items == []
    assert world.audit_entries() == []
