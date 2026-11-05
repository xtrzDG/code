"""Quiet hours, push endpoint checks, staff e-mails and settings."""

from datetime import UTC, datetime

import pytest
from typed_time_provider import Microseconds

from app.containers.notification_factories import build_web_push_client
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.domain.notification_preferences import QuietHours
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.notifications.push_endpoints import (
    are_valid_push_keys,
    is_supported_push_endpoint,
)
from app.utilities.notifications.quiet_hours import (
    is_valid_quiet_hours,
    quiet_hours_end,
)
from app.utilities.notifications.staff_email import build_staff_email
from app.utilities.scheduling.zoned_time import load_time_zone
from tests.notifications.test_web_push_encryption import (
    AUTH_SECRET,
    RECEIVER_PUBLIC,
    SENDER_PRIVATE,
    SENDER_PUBLIC,
)

EXPIRES = Microseconds(1_790_000_000_000_000)
TBILISI = load_time_zone(TimezoneName("Asia/Tbilisi"))


def at(text: str) -> Microseconds:
    return Microseconds(int(datetime.fromisoformat(text).timestamp() * 1_000_000))


def hours(starts: str, ends: str) -> QuietHours:
    return QuietHours(starts_at=LocalTimeOfDay(starts), ends_at=LocalTimeOfDay(ends))


def test_quiet_hours_across_midnight_end_the_next_morning() -> None:
    night = hours("22:00", "08:00")

    assert quiet_hours_end(night, TBILISI, at("2026-10-05T23:30:00+04:00")) == at(
        "2026-10-06T08:00:00+04:00"
    )
    assert quiet_hours_end(night, TBILISI, at("2026-10-06T03:00:00+04:00")) == at(
        "2026-10-06T08:00:00+04:00"
    )
    assert quiet_hours_end(night, TBILISI, at("2026-10-06T08:00:00+04:00")) is None
    assert quiet_hours_end(night, TBILISI, at("2026-10-06T21:59:00+04:00")) is None


def test_daytime_quiet_hours_and_none() -> None:
    lunch = hours("13:00", "14:00")

    assert quiet_hours_end(lunch, TBILISI, at("2026-10-05T13:30:00+04:00")) == at(
        "2026-10-05T14:00:00+04:00"
    )
    assert quiet_hours_end(lunch, TBILISI, at("2026-10-05T14:30:00+04:00")) is None
    assert quiet_hours_end(None, TBILISI, at("2026-10-05T13:30:00+04:00")) is None
    assert not is_valid_quiet_hours(hours("09:00", "09:00"))
    assert quiet_hours_end(hours("09:00", "09:00"), TBILISI, EXPIRES) is None


def test_quiet_hours_follow_the_wall_clock_over_a_dst_change() -> None:
    berlin = load_time_zone(TimezoneName("Europe/Berlin"))
    night = hours("22:00", "08:00")

    # The clocks go back at 03:00 on 2026-10-25: 08:00 is UTC+1 that day.
    assert quiet_hours_end(night, berlin, at("2026-10-24T23:00:00+02:00")) == at(
        "2026-10-25T08:00:00+01:00"
    )
    assert datetime.fromtimestamp(0, UTC).year == 1970


@pytest.mark.parametrize(
    ("endpoint", "environment", "expected"),
    [
        ("https://fcm.googleapis.com/fcm/send/abc", "production", True),
        ("https://updates.push.services.mozilla.com/wpush/v2/x", "production", True),
        ("https://web.push.apple.com/QF4", "production", True),
        ("https://wns2-db5p.notify.windows.com/w/?token=x", "production", True),
        ("https://evil.example.com/fcm.googleapis.com", "production", False),
        ("https://fcm.googleapis.com.evil.com/x", "production", False),
        ("http://fcm.googleapis.com/x", "production", False),
        ("https://fcm.googleapis.com:8443/x", "production", False),
        ("https://user:pw@fcm.googleapis.com/x", "production", False),
        ("http://localhost:9999/push", "production", False),
        ("http://localhost:9999/push", "development", True),
    ],
)
def test_only_known_push_services_are_accepted(
    endpoint: str, environment: str, expected: bool
) -> None:
    assert (
        is_supported_push_endpoint(endpoint, DeploymentEnvironment(environment))
        is expected
    )


def test_push_keys_must_be_a_point_and_a_16_byte_secret() -> None:
    assert are_valid_push_keys(RECEIVER_PUBLIC, AUTH_SECRET)
    assert not are_valid_push_keys(RECEIVER_PUBLIC, RECEIVER_PUBLIC)
    assert not are_valid_push_keys("B" + "A" * 86, AUTH_SECRET)
    assert not are_valid_push_keys("!!!", AUTH_SECRET)


def test_a_staff_email_has_a_subject_a_button_and_escaped_text() -> None:
    email = build_staff_email(
        MessageText(
            "Urgent: a customer needs a person\n<b>Salon</b> · Complaint\n"
            "Open: https://app.example.com/n/AAAA"
        )
    )

    assert email.subject == "Urgent: a customer needs a person"
    assert "Open: https://app.example.com/n/AAAA" in str(email.text_body)
    assert '<a href="https://app.example.com/n/AAAA"' in str(email.html_body)
    assert ">Open</a>" in str(email.html_body)
    assert "&lt;b&gt;Salon&lt;/b&gt;" in str(email.html_body)
    long = build_staff_email(MessageText("x" * 400))
    assert len(str(long.subject)) == 150 and str(long.subject).endswith("…")
    assert build_staff_email(MessageText("")).subject == "Assistant Workshop"


def test_web_push_settings_come_all_together() -> None:
    assert build_web_push_client(assemble_app_settings({})) is None
    complete = assemble_app_settings(
        {
            "WEB_PUSH_VAPID_PUBLIC_KEY": SENDER_PUBLIC,
            "WEB_PUSH_VAPID_PRIVATE_KEY": SENDER_PRIVATE,
            "WEB_PUSH_VAPID_SUBJECT": "mailto:ops@example.com",
        }
    )
    client = build_web_push_client(complete)
    assert client is not None and client.public_key == SENDER_PUBLIC

    with pytest.raises(ValidationFailedError, match="together"):
        assemble_app_settings({"WEB_PUSH_VAPID_PUBLIC_KEY": SENDER_PUBLIC})
