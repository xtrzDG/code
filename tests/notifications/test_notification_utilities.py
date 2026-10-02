"""Signed links, quiet hours, push endpoint checks, staff e-mails and settings."""

import base64
import struct
from datetime import UTC, datetime

import pytest
from typed_time_provider import Microseconds

from app.containers.notification_factories import build_web_push_client
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.domain.notification_preferences import QuietHours
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.schemas.typings.notifications.constrained_strings import StaffLinkToken
from app.schemas.typings.platform.strings import PlatformSecret
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
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from app.utilities.scheduling.zoned_time import load_time_zone
from tests.notifications.test_web_push_encryption import (
    AUTH_SECRET,
    RECEIVER_PUBLIC,
    SENDER_PRIVATE,
    SENDER_PUBLIC,
)

KEY = PlatformSecret("a-long-enough-encryption-key-for-the-tests")
EXPIRES = Microseconds(1_790_000_000_000_000)
TBILISI = load_time_zone(TimezoneName("Asia/Tbilisi"))


def at(text: str) -> Microseconds:
    return Microseconds(int(datetime.fromisoformat(text).timestamp() * 1_000_000))


@pytest.mark.parametrize(
    "claims",
    [
        StaffLinkClaims(
            business_id=BusinessId(),
            target=StaffLinkTarget.CONVERSATION,
            conversation_id=ConversationId(),
            expires_at=EXPIRES,
        ),
        StaffLinkClaims(
            business_id=BusinessId(),
            target=StaffLinkTarget.LEAD,
            lead_id=LeadId(),
            expires_at=EXPIRES,
        ),
        StaffLinkClaims(
            business_id=BusinessId(),
            target=StaffLinkTarget.BOOKING,
            booking_id=BookingId(),
            expires_at=EXPIRES,
        ),
        StaffLinkClaims(
            business_id=BusinessId(),
            target=StaffLinkTarget.NOTIFICATIONS,
            expires_at=EXPIRES,
        ),
    ],
)
def test_signed_links_carry_their_page_and_are_short(claims: StaffLinkClaims) -> None:
    signer = StaffLinkSigner(KEY)

    token = signer.sign(claims)

    assert len(token) == 67
    assert signer.read(token) == claims


def test_altered_foreign_and_malformed_tokens_are_refused() -> None:
    signer = StaffLinkSigner(KEY)
    claims = StaffLinkClaims(
        business_id=BusinessId(),
        target=StaffLinkTarget.NOTIFICATIONS,
        expires_at=EXPIRES,
    )
    token = str(signer.sign(claims))
    raw = base64.urlsafe_b64decode(token + "=")
    altered = base64.urlsafe_b64encode(raw[:5] + bytes([raw[5] ^ 1]) + raw[6:])

    assert signer.read(StaffLinkToken(altered.rstrip(b"=").decode())) is None
    assert StaffLinkSigner(PlatformSecret("x" * 40)).read(StaffLinkToken(token)) is None
    assert signer.read(StaffLinkToken(token[:-4])) is None
    assert signer.read(StaffLinkToken("A" * 66 + "-")) is None

    payload = struct.pack("!B16sB16sI", 2, bytes(16), 1, bytes(16), 1)
    resigned = payload + signer._signature(payload)  # noqa: SLF001
    encoded = base64.urlsafe_b64encode(resigned).rstrip(b"=").decode()
    assert signer.read(StaffLinkToken(encoded)) is None
    unknown_target = struct.pack("!B16sB16sI", 1, bytes(16), 9, bytes(16), 1)
    encoded = (
        base64.urlsafe_b64encode(unknown_target + signer._signature(unknown_target))  # noqa: SLF001
        .rstrip(b"=")
        .decode()
    )
    assert signer.read(StaffLinkToken(encoded)) is None


def test_without_an_encryption_key_links_still_work_within_the_process() -> None:
    signer = StaffLinkSigner(None)
    claims = StaffLinkClaims(
        business_id=BusinessId(),
        target=StaffLinkTarget.NOTIFICATIONS,
        expires_at=EXPIRES,
    )

    assert signer.read(signer.sign(claims)) == claims
    assert StaffLinkSigner(None).read(signer.sign(claims)) is None


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
