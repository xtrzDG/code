"""Who gets a stored report, where and when (the owner digest facilitator)."""

import json
from datetime import datetime

from app.schemas.constants.users import BusinessMemberRole
from app.schemas.constants.value import ValueReportKind
from app.schemas.domain.businesses import BusinessMember
from app.schemas.domain.notification_preferences import (
    QuietHours,
    StaffNotificationPreferences,
    UserNotificationPreferencesDocument,
)
from app.schemas.domain.value_settings import DigestPreferencesDocument
from app.schemas.dto.value.value_reports import ValueReportView
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.utilities.notifications.staff_delivery_keys import preferences_id_of
from app.utilities.value.value_keys import digest_preferences_id_of, value_report_id_of
from tests.operations.fakes import RecordingManagerNotifier, to_microseconds
from tests.value.value_scene import ValueScene

TOTALS: dict[str, int] = {
    "conversation_count": 40,
    "after_hours_conversation_count": 12,
    "customer_message_count": 160,
    "assistant_reply_count": 150,
    "call_count": 6,
    "booking_count": 22,
    "assistant_booking_count": 20,
    "request_count": 3,
    "handoff_count": 2,
    "staff_minutes_saved": 205,
    "estimated_revenue_minor": 240_000,
}


def weekly_report(scene: ValueScene) -> ValueReportView:
    report_id = value_report_id_of(
        scene.business.id,
        ValueReportKind.WEEKLY,
        "2026-W40",  # type: ignore[arg-type]
    )
    return ValueReportView.model_validate_json(
        json.dumps(
            {
                "id": str(report_id),
                "business_id": str(scene.business.id),
                "kind": "weekly",
                "period_key": "2026-W40",
                "date_from": "2026-09-28",
                "date_to": "2026-10-04",
                "previous_date_from": "2026-09-21",
                "previous_date_to": "2026-09-27",
                "currency_code": "GEL",
                "value_basis": "bookings",
                "average_check_minor": 12_000,
                "average_check_source": "owner",
                "current": TOTALS,
                "previous": {**TOTALS, "assistant_booking_count": 16},
                "delivery": "sent",
                "recipient_count": 0,
                "created_at": 1,
            }
        )
    )


def test_every_owner_who_wants_it_gets_it_and_staff_never_do() -> None:
    scene = ValueScene()
    second_owner = scene.add_user("partner@example.com", "en")
    phone_owner = scene.add_user(None, "ka")
    scene.business.members.extend(
        [
            BusinessMember(user_id=second_owner.id, role=BusinessMemberRole.OWNER),
            BusinessMember(user_id=phone_owner.id, role=BusinessMemberRole.OWNER),
        ]
    )
    scene.world.business_repo.save(scene.business)
    scene.device(phone_owner, "ka")
    scene.world.digest_preferences_repo.save(
        DigestPreferencesDocument(
            id=digest_preferences_id_of(scene.business.id, second_owner.id),
            business_id=scene.business.id,
            user_id=second_owner.id,
            is_weekly_digest_on=False,
        )
    )

    count = scene.world.owner_digests().send(scene.business, weekly_report(scene))

    assert count == 2  # the first owner's e-mail, the phone owner's device
    [email] = scene.world.notifier.notifications
    assert str(email.contact.address) == "owner@example.com"
    assert str(email.text).startswith("Ваш помощник за неделю · Salobie Bia")
    [push] = scene.world.push_queue.queued
    assert push.user_id == phone_owner.id
    assert str(push.brief.title) == "თქვენი ასისტენტი გასულ კვირას · Salobie Bia"
    assert str(push.tag) == "value_report:weekly"
    assert push.deliver_after is None


def test_a_device_waits_for_the_end_of_its_quiet_hours() -> None:
    scene = ValueScene()  # Monday 12:00 in Tbilisi.
    scene.device(scene.owner, "en")
    scene.world.notification_preferences_repo.save(
        UserNotificationPreferencesDocument(
            id=preferences_id_of(scene.business.id, scene.owner.id),
            business_id=scene.business.id,
            user_id=scene.owner.id,
            preferences=StaffNotificationPreferences(
                quiet_hours=QuietHours(
                    starts_at=LocalTimeOfDay("11:00"), ends_at=LocalTimeOfDay("14:00")
                )
            ),
        )
    )

    scene.world.owner_digests().send(scene.business, weekly_report(scene))

    [push] = scene.world.push_queue.queued
    assert push.deliver_after == to_microseconds(
        datetime.fromisoformat("2026-10-05T14:00:00+04:00")
    )
    # The e-mail is not held: it waits in the inbox anyway.
    assert scene.world.notifier.notifications[0].deliver_after is None


def test_a_failing_recipient_does_not_stop_the_others() -> None:
    scene = ValueScene()
    other = scene.add_user("second@example.com", "en")
    scene.business.members.insert(
        0, BusinessMember(user_id=other.id, role=BusinessMemberRole.OWNER)
    )
    scene.world.business_repo.save(scene.business)
    scene.world.notifier = RecordingManagerNotifier(
        raising_addresses=frozenset({"second@example.com"})
    )

    count = scene.world.owner_digests().send(scene.business, weekly_report(scene))

    assert count == 1
    assert [
        str(note.contact.address) for note in scene.world.notifier.notifications
    ] == ["owner@example.com"]
