"""
The parts of the login abuse protection: cap alerts (e-mail and Sentry),
the high-cost number registry and the settings.
"""

import pytest
import sentry_sdk
from typed_time_provider import Microseconds, WallClock

from app.facilitators.users.login_code_cap_alert_facilitator import (
    LoginCodeCapAlertFacilitator,
)
from app.registries.localization.high_cost_phone_number_registry import (
    HighCostPhoneNumberRegistry,
)
from app.schemas.constants.users import LoginCodeCap
from app.schemas.dto.login_protection import LoginCodeCapAlert
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    PhoneNumberPrefix,
)
from app.schemas.typings.messaging.strings import EmailBodyText, EmailSubject
from app.schemas.typings.users.constrained_integers import OtpSendLimit
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.users.accounts_clock import AdjustableClock

ADMINS: list[EmailAddress] = [
    EmailAddress("ops@example.com"),
    EmailAddress("founder@example.com"),
]
COUNTRY_ALERT = LoginCodeCapAlert(
    cap=LoginCodeCap.COUNTRY, limit=OtpSendLimit(100), country_code=CountryCode("TV")
)


class RecordingEmailClient:
    def __init__(self, failing_recipient: EmailAddress | None = None) -> None:
        self.sent: list[tuple[EmailAddress, EmailSubject, EmailBodyText]] = []
        self.failing_recipient: EmailAddress | None = failing_recipient

    def send_email(
        self,
        recipient: EmailAddress,
        subject: EmailSubject,
        text_body: EmailBodyText,
        html_body: EmailBodyText | None,
    ) -> None:
        del html_body
        if recipient == self.failing_recipient:
            raise ExternalServiceError("SMTP refused the message.")

        self.sent.append((recipient, subject, text_body))


def build_alerts(
    email_client: RecordingEmailClient | None,
) -> tuple[LoginCodeCapAlertFacilitator, AdjustableClock, list[str]]:
    clock = AdjustableClock()
    wall_clock: WallClock[Microseconds] = clock.build_wall_clock()
    return LoginCodeCapAlertFacilitator(email_client, ADMINS, wall_clock), clock, []


def test_a_cap_alert_reaches_sentry_and_every_platform_admin_once_an_hour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email_client = RecordingEmailClient()
    alerts, clock, events = build_alerts(email_client)

    def record_event(message: str, level: str) -> None:
        events.append(f"{level}: {message}")

    monkeypatch.setattr(sentry_sdk, "capture_message", record_event)

    alerts.report_cap_reached(COUNTRY_ALERT)
    alerts.report_cap_reached(COUNTRY_ALERT)

    assert events == [
        "warning: Login code cap reached for TV: 100 login codes to phones of "
        "one country (OTP_SENDS_PER_COUNTRY_PER_HOUR) in the last hour."
    ]
    assert [recipient for recipient, _, _ in email_client.sent] == ADMINS
    subject, body = email_client.sent[0][1], email_client.sent[0][2]
    assert str(subject).startswith("[Assistant Workshop] Login code cap reached")
    assert "OTP_HIGH_RISK_COUNTRIES" in str(body)

    # Another cap alerts at once; the same cap again after an hour.
    alerts.report_cap_reached(
        LoginCodeCapAlert(cap=LoginCodeCap.NEW_DESTINATIONS, limit=OtpSendLimit(300))
    )
    clock.advance(3601)
    alerts.report_cap_reached(COUNTRY_ALERT)
    assert len(events) == 3


def test_an_alert_never_fails_the_refused_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_sentry(message: str, level: str) -> None:
        raise RuntimeError("Sentry is down")

    monkeypatch.setattr(sentry_sdk, "capture_message", broken_sentry)
    email_client = RecordingEmailClient(failing_recipient=ADMINS[0])
    alerts, _, _ = build_alerts(email_client)

    alerts.report_cap_reached(COUNTRY_ALERT)

    assert [recipient for recipient, _, _ in email_client.sent] == ADMINS[1:]
    without_email, _, _ = build_alerts(None)
    without_email.report_cap_reached(COUNTRY_ALERT)


@pytest.mark.parametrize(
    ("phone_number", "is_high_cost"),
    [
        ("+449098790000", True),  # UK premium rate (09).
        ("+447012345678", True),  # UK personal number (070).
        ("+33899123456", True),  # French premium rate (089).
        ("+8816123456", True),  # Iridium satellite phone.
        ("+995555123456", False),  # Georgian mobile.
        ("+4915112345678", False),  # German mobile.
        ("+447624123456", False),  # Isle of Man mobile.
        ("+99912345678", True),  # No such calling code: never sent.
    ],
)
def test_high_cost_numbers(phone_number: str, is_high_cost: bool) -> None:
    registry = HighCostPhoneNumberRegistry([])

    assert registry.is_high_cost(E164PhoneNumber(phone_number)) is is_high_cost


def test_denied_prefixes_extend_the_high_cost_numbers() -> None:
    registry = HighCostPhoneNumberRegistry([PhoneNumberPrefix("+4915")])

    assert registry.is_high_cost(E164PhoneNumber("+4915112345678"))
    assert not registry.is_high_cost(E164PhoneNumber("+995555123456"))


def test_login_protection_settings_have_safe_defaults() -> None:
    settings = assemble_app_settings({})

    assert int(settings.otp_sends_per_country_per_hour) == 100
    assert int(settings.otp_sends_to_verified_users_per_hour) == 300
    assert int(settings.otp_verifies_per_ip_per_10_minutes) == 20
    assert CountryCode("TV") in settings.otp_high_risk_country_codes
    assert settings.otp_denied_phone_prefixes == []
    assert settings.turnstile_site_key is None
    assert settings.turnstile_secret_key is None


def test_login_protection_settings_are_read_and_checked() -> None:
    settings = assemble_app_settings(
        {
            "OTP_HIGH_RISK_COUNTRIES": "",
            "OTP_DENIED_PHONE_PREFIXES": "+4490, +882",
            "TURNSTILE_SITE_KEY": "0x4AAAAAAABkMYinukE8nzY",
            "TURNSTILE_SECRET_KEY": "0x4AAAA-secret",
        }
    )

    assert settings.otp_high_risk_country_codes == []
    assert settings.otp_denied_phone_prefixes == [
        PhoneNumberPrefix("+4490"),
        PhoneNumberPrefix("+882"),
    ]
    assert str(settings.turnstile_site_key) == "0x4AAAAAAABkMYinukE8nzY"

    with pytest.raises(ValidationFailedError, match="TURNSTILE_SITE_KEY"):
        assemble_app_settings({"TURNSTILE_SECRET_KEY": "0x4AAAA-secret"})
    with pytest.raises(ValidationFailedError, match="OTP_DENIED_PHONE_PREFIXES"):
        assemble_app_settings({"OTP_DENIED_PHONE_PREFIXES": "4490"})
    with pytest.raises(ValidationFailedError, match="OTP_HIGH_RISK_COUNTRIES"):
        assemble_app_settings({"OTP_HIGH_RISK_COUNTRIES": "Tuvalu"})
