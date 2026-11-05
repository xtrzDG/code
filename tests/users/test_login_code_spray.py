"""
One client network asking sign-in codes for many different phones and
e-mails within an hour alerts the platform team once an hour, naming the
network only; a few people on one network do not.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds, WallClock

from app.contracts.messaging_clients import EmailSenderClientContract
from app.facilitators.users.sign_in_code_spray_alert_facilitator import (
    SignInCodeSprayAlertFacilitator,
    describe_spray,
)
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.dto.sign_in_alerts import SignInCodeSprayAlert
from app.schemas.typings.compliance.strings import ClientNetwork
from app.schemas.typings.messaging.strings import EmailBodyText, EmailSubject
from app.schemas.typings.users.constrained_integers import OtpDestinationCount
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.use_cases.users.otp_login.login_code_spray import (
    SPRAY_DESTINATIONS_PER_NETWORK,
)
from tests.users.accounts_testbed import build_accounts_testbed
from tests.users.test_start_login_throttling import georgian_number, request_from

LIMITS: dict[str, str] = {"OTP_SENDS_PER_IP_PER_HOUR": "100"}


def test_codes_for_many_numbers_from_one_network_alert_the_admins() -> None:
    testbed = build_accounts_testbed(LIMITS)
    threshold: int = int(SPRAY_DESTINATIONS_PER_NETWORK)
    for index in range(threshold - 1):
        # Rotating IPv6 addresses of one /64 count as one network.
        request_from(testbed, georgian_number(index), f"2001:db8:5:7::{index + 1}")
    assert testbed.spray_alerts.alerts == []

    request_from(testbed, georgian_number(threshold), "2001:db8:5:7::ff")

    [alert] = testbed.spray_alerts.alerts
    assert str(alert.client_network) == "2001:db8:5:7::/64"
    assert int(alert.destination_count) == threshold
    assert "+995" not in describe_spray(alert)


def test_the_same_number_again_or_other_networks_are_no_spray() -> None:
    testbed = build_accounts_testbed(LIMITS)
    for index in range(int(SPRAY_DESTINATIONS_PER_NETWORK) + 2):
        request_from(testbed, georgian_number(index), f"198.51.100.{index + 1}")
    for _ in range(3):
        testbed.clock.advance(31)
        request_from(testbed, georgian_number(0), "203.0.113.7")

    assert testbed.spray_alerts.alerts == []


class RecordingEmail(EmailSenderClientContract):
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_email(
        self,
        recipient: EmailAddress,
        subject: EmailSubject,
        text_body: EmailBodyText,
        html_body: EmailBodyText | None,
        attachments: Sequence[EmailAttachment] = (),
    ) -> None:
        self.sent.append((str(recipient), str(subject)))


def test_one_e_mail_per_network_and_hour() -> None:
    now_ns: list[int] = [0]
    email = RecordingEmail()
    facilitator = SignInCodeSprayAlertFacilitator(
        email,
        [EmailAddress("security@platform.example")],
        WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: now_ns[0],
        ),
    )
    alert = SignInCodeSprayAlert(
        client_network=ClientNetwork("198.51.100.7"),
        destination_count=OtpDestinationCount(14),
        threshold=SPRAY_DESTINATIONS_PER_NETWORK,
    )

    facilitator.report_code_spray(alert)
    facilitator.report_code_spray(alert)
    now_ns[0] = (3_600 * 1_000_000 + 1) * 1_000
    facilitator.report_code_spray(alert)

    assert [recipient for recipient, _ in email.sent] == [
        "security@platform.example"
    ] * 2
    assert "198.51.100.7" in email.sent[0][1]
