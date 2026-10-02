"""Staff alerts reach every contact and device, as each prefers."""

from datetime import datetime

from typed_time_provider import Microseconds

from app.schemas.constants.handoffs import HandoffUrgency
from app.schemas.constants.notifications import StaffAlertEvent, StaffLinkTarget
from app.schemas.domain.notification_preferences import (
    QuietHours,
    StaffNotificationPreferences,
    UserNotificationPreferencesDocument,
)
from app.schemas.dto.notifications.staff_alerts import StaffAlert, StaffAlertBrief
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import StaffLinkToken
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.notifications.staff_alerts import StaffAlertTexts, handoff_alert
from app.utilities.notifications.staff_delivery_keys import preferences_id_of
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from tests.notifications.alert_world import CABINET, AlertWorld
from tests.notifications.staff_alert_fakes import (
    TEST_ENCRYPTION_KEY,
    settings_without_cabinet,
)
from tests.operations.fakes import RecordingManagerNotifier

QUIET_NIGHT = QuietHours(
    starts_at=LocalTimeOfDay("22:00"), ends_at=LocalTimeOfDay("08:00")
)


def texts() -> StaffAlertTexts:
    return StaffAlertTexts(
        detailed=lambda language: MessageText(f"[{language}] Tooth hurts, +995"),
        brief=lambda language: StaffAlertBrief(
            title=StaffAlertTitle(f"[{language}] A customer needs a person"),
            detail=StaffAlertDetail("Salobie Bia · Complaint"),
        ),
    )


def handoff(world: AlertWorld, urgency: HandoffUrgency) -> StaffAlert:
    return handoff_alert(
        world.business.id, HandoffId(), ConversationId(), urgency=urgency
    )


def texts_by_address(world: AlertWorld) -> dict[str, str]:
    return {str(contact.address): str(text) for contact, text in world.notifier.sent}


def test_linked_chats_get_details_and_others_the_brief_with_a_signed_link() -> None:
    world = AlertWorld()
    sent = handoff(world, HandoffUrgency.NORMAL)

    queued = world.alerts.alert(world.business, sent, texts())

    assert int(queued) == 3
    by_address = texts_by_address(world)
    telegram, email, sms = (
        by_address["4242"],
        by_address["anna@example.com"],
        by_address["+995555000222"],
    )
    assert telegram.startswith("[ka] Tooth hurts, +995\nგახსნა: https://")
    assert email.startswith(
        "[en] A customer needs a person\nSalobie Bia · Complaint\nOpen: "
    )
    assert sms.startswith("[ru] A customer needs a person\n")
    assert "+995" not in email and "Tooth" not in sms
    link = email.rsplit(" ", 1)[1]
    assert link.startswith(f"{CABINET}/n/")
    claims = StaffLinkSigner(TEST_ENCRYPTION_KEY).read(
        StaffLinkToken(link.removeprefix(f"{CABINET}/n/"))
    )
    assert claims is not None
    assert claims.target is StaffLinkTarget.CONVERSATION
    assert claims.conversation_id == sent.conversation_id
    assert int(claims.expires_at) > int(world.clock.now_microseconds())
    assert all(
        notification.handoff_id == sent.handoff_id
        and notification.deliver_after is None
        for notification in world.notifier.notifications
    )


def test_without_the_cabinet_address_no_link_is_added() -> None:
    world = AlertWorld(settings_without_cabinet())

    world.alerts.alert(world.business, handoff(world, HandoffUrgency.LOW), texts())

    assert "Open:" not in texts_by_address(world)["anna@example.com"]


def test_contacts_choose_their_events_and_quiet_hours() -> None:
    world = AlertWorld()
    nino, anna, gio = world.business.manager_contacts
    world.business.manager_contacts = [
        nino.model_copy(
            update={
                "preferences": StaffNotificationPreferences(
                    events=[StaffAlertEvent.LEAD]
                )
            }
        ),
        anna.model_copy(
            update={
                "preferences": StaffNotificationPreferences(quiet_hours=QUIET_NIGHT)
            }
        ),
        gio,
    ]
    world.clock.move_to(datetime.fromisoformat("2026-10-05T23:30:00+04:00"))

    queued = world.alerts.alert(
        world.business, handoff(world, HandoffUrgency.NORMAL), texts()
    )

    assert int(queued) == 2
    held = {
        str(notification.contact.address): notification.deliver_after
        for notification in world.notifier.notifications
    }
    assert set(held) == {"anna@example.com", "+995555000222"}
    morning = datetime.fromisoformat("2026-10-06T08:00:00+04:00")
    assert held["anna@example.com"] == Microseconds(
        int(morning.timestamp()) * 1_000_000
    )
    assert held["+995555000222"] is None


def test_urgent_handoffs_come_through_quiet_hours() -> None:
    world = AlertWorld()
    world.business.manager_contacts = [
        contact.model_copy(
            update={
                "preferences": StaffNotificationPreferences(quiet_hours=QUIET_NIGHT)
            }
        )
        for contact in world.business.manager_contacts
    ]
    world.clock.move_to(datetime.fromisoformat("2026-10-05T23:30:00+04:00"))

    world.alerts.alert(world.business, handoff(world, HandoffUrgency.CRITICAL), texts())

    assert [n.deliver_after for n in world.notifier.notifications] == [None] * 3


def test_member_devices_get_the_brief_in_their_language_as_each_prefers() -> None:
    world = AlertWorld()
    phone = world.add_device(world.owner, "ru")
    laptop = world.add_device(world.owner, "en")
    staff_phone = world.add_device(world.staff, "ka")
    world.preferences.save(
        UserNotificationPreferencesDocument(
            id=preferences_id_of(world.business.id, world.staff),
            business_id=world.business.id,
            user_id=world.staff,
            preferences=StaffNotificationPreferences(events=[StaffAlertEvent.BOOKING]),
        )
    )
    stranger_device = world.add_device(UserId(), "en")
    sent = handoff(world, HandoffUrgency.HIGH)

    queued = world.alerts.alert(world.business, sent, texts())

    assert int(queued) == 5
    pushed = {str(item.subscription_id): item for item in world.push_queue.queued}
    assert set(pushed) == {str(phone.id), str(laptop.id)}
    assert str(pushed[str(phone.id)].brief.title).startswith("[ru]")
    assert pushed[str(laptop.id)].is_urgent
    assert pushed[str(laptop.id)].tag == f"handoff:{sent.handoff_id}"
    assert str(pushed[str(laptop.id)].link).startswith(f"{CABINET}/n/")
    assert staff_phone.id not in {
        item.subscription_id for item in world.push_queue.queued
    }
    # A device of someone no longer in the team is forgotten.
    assert world.subscriptions.get(world.business.id, stranger_device.id) is None


def test_a_failing_contact_never_stops_the_others() -> None:
    world = AlertWorld()
    world.notifier = RecordingManagerNotifier(
        failing_addresses=frozenset({"+995555000222"}),
        raising_addresses=frozenset({"4242"}),
    )
    world.alerts._manager_notifier = world.notifier  # noqa: SLF001

    queued = world.alerts.alert(
        world.business, handoff(world, HandoffUrgency.NORMAL), texts()
    )

    assert int(queued) == 1
    assert [str(contact.address) for contact, _ in world.notifier.sent] == [
        "anna@example.com",
        "+995555000222",
    ]


def test_texts_are_rendered_once_per_language() -> None:
    calls: list[str] = []

    def detailed(language: LanguageTag) -> MessageText:
        calls.append(str(language))
        return MessageText("details")

    shared = StaffAlertTexts(
        detailed=detailed,
        brief=lambda language: StaffAlertBrief(title=StaffAlertTitle("t")),
    )

    shared.detailed(LanguageTag("ka"))
    shared.detailed(LanguageTag("ka"))
    shared.brief(LanguageTag("en"))
    shared.brief(LanguageTag("en"))

    assert calls == ["ka"]
