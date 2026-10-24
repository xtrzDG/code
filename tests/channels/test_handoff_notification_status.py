"""A handoff follows the delivery of its staff notifications through the outbox."""

from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffStatus,
    ManagerContactChannel,
)
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import (
    HandoffSummary,
    ManagerContactAddress,
    ManagerName,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.channels_payloads import telegram_ok
from tests.channels.outbox_reads import outbox_of
from tests.channels.testbed import ChannelsTestbed

REFUSED: dict[str, object] = {
    "ok": False,
    "error_code": 400,
    "description": "Bad Request: chat not found",
}


def staff(address: str) -> ManagerContact:
    return ManagerContact(
        name=ManagerName("Nino"),
        channel=ManagerContactChannel.TELEGRAM,
        address=ManagerContactAddress(address),
        language=LanguageTag("ka"),
    )


def open_handoff(testbed: ChannelsTestbed) -> HandoffDocument:
    owner = testbed.add_user("owner")
    business = testbed.add_business(owner)
    handoff = HandoffDocument(
        business_id=business.id,
        conversation_id=ConversationId(),
        contact_id=ContactId(),
        reason=HandoffReason.COMPLAINT,
        summary=HandoffSummary("The guest is unhappy."),
    )
    testbed.handoff_repo.save(handoff)
    return handoff


def notify(testbed: ChannelsTestbed, handoff: HandoffDocument, address: str) -> bool:
    return testbed.staff_notifier.notify(
        StaffNotification(
            business_id=handoff.business_id,
            contact=staff(address),
            text=MessageText("Handoff: the guest is unhappy."),
            handoff_id=handoff.id,
        )
    )


def stored(testbed: ChannelsTestbed, handoff: HandoffDocument) -> HandoffDocument:
    current = testbed.handoff_repo.get(handoff.business_id, handoff.id)
    assert current is not None
    return current


def test_a_delivered_notification_marks_the_handoff_notified() -> None:
    testbed = ChannelsTestbed()
    handoff = open_handoff(testbed)
    testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))

    assert notify(testbed, handoff, "101")
    assert stored(testbed, handoff).status is HandoffStatus.PENDING

    testbed.run_worker()

    assert stored(testbed, handoff).status is HandoffStatus.NOTIFIED


def test_a_handoff_is_notified_once_per_contact_however_often_it_is_sent() -> None:
    testbed = ChannelsTestbed()
    handoff = open_handoff(testbed)
    testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))

    assert notify(testbed, handoff, "101")
    assert notify(testbed, handoff, "101")
    testbed.run_worker()

    assert len(outbox_of(testbed, handoff.business_id)) == 1
    assert len(testbed.telegram_transport.requests_to("/sendMessage")) == 1


def test_a_refused_notification_fails_the_handoff_until_another_arrives() -> None:
    testbed = ChannelsTestbed()
    handoff = open_handoff(testbed)
    testbed.telegram_transport.respond_in_turn(
        "POST",
        r"/sendMessage$",
        [(400, REFUSED), (200, telegram_ok({}))],
    )

    notify(testbed, handoff, "101")
    testbed.run_worker()
    assert stored(testbed, handoff).status is HandoffStatus.NOTIFICATION_FAILED

    notify(testbed, handoff, "202")
    testbed.run_worker()
    assert stored(testbed, handoff).status is HandoffStatus.NOTIFIED


def test_a_resolved_handoff_stays_resolved() -> None:
    testbed = ChannelsTestbed()
    handoff = open_handoff(testbed)
    testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))
    notify(testbed, handoff, "101")
    resolved = stored(testbed, handoff)
    resolved.status = HandoffStatus.RESOLVED
    testbed.handoff_repo.save(resolved)

    testbed.run_worker()

    assert stored(testbed, handoff).status is HandoffStatus.RESOLVED
