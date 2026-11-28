"""
Whether the platform can send SMS: the Twilio account (SID and token) with
a sender. The account alone rents numbers and signs the call fallback, but
sends no SMS, and whoever asks why reads that the sender is pending.
"""

import logging

import pytest
from pydantic import ValidationError

from app.containers.factories import build_twilio_messaging_client
from app.gateways.startup_checks import run_startup_checks
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.messaging import SmsUnavailableReason
from app.schemas.domain.businesses import ManagerContact
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.messaging import TwilioSmsSender
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.config_helpers.sms_sender import (
    SMS_OFF_MESSAGE,
    platform_sms_sender,
    platform_sms_unavailable_reason,
    report_sms_sender,
)
from app.utilities.notifications.staff_providers import (
    MISSING_PROVIDER_TEXTS,
    MISSING_SMS_SENDER_TEXT,
    is_provider_configured,
    missing_staff_provider,
    report_missing_provider,
)
from tests.channels.channels_settings import build_settings
from tests.channels.outbox_reads import outbox_of
from tests.channels.testbed import ChannelsTestbed
from tests.platform.production_settings import container_with

ACCOUNT_SID: str = "AC" + "1f" * 16
TWILIO_ACCOUNT: dict[str, str] = {
    "TWILIO_ACCOUNT_SID": ACCOUNT_SID,
    "TWILIO_AUTH_TOKEN": "fake-twilio-auth-token",
}
FROM_NUMBER: dict[str, str] = {"TWILIO_FROM_NUMBER": "+15005550006"}
MESSAGING_SERVICE: dict[str, str] = {"TWILIO_MESSAGING_SERVICE_SID": "MG" + "0" * 32}
SENDER_SETTINGS: str = "TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID"
REPORT_LOGGER: str = "app.utilities.config_helpers.sms_sender"


def settings(environment: str = "development", **variables: str) -> AppSettings:
    return assemble_app_settings({"APP_ENV": environment, **variables})


def sms_contact() -> ManagerContact:
    return ManagerContact(
        name=ManagerName("Levan"),
        channel=ManagerContactChannel.SMS,
        address=ManagerContactAddress("+995599123456"),
        language=LanguageTag("en"),
    )


@pytest.mark.parametrize(
    ("variables", "reason"),
    [
        ({}, SmsUnavailableReason.NOT_CONFIGURED),
        (TWILIO_ACCOUNT, SmsUnavailableReason.NO_SENDER),
        ({**TWILIO_ACCOUNT, **FROM_NUMBER}, None),
        ({**TWILIO_ACCOUNT, **MESSAGING_SERVICE}, None),
    ],
)
def test_sms_needs_the_account_and_a_sender(
    variables: dict[str, str], reason: SmsUnavailableReason | None
) -> None:
    app_settings = settings(**variables)
    sender = platform_sms_sender(app_settings)

    assert platform_sms_unavailable_reason(app_settings) is reason
    assert (sender is None) is (reason is not None)
    assert (build_twilio_messaging_client(app_settings) is None) is (reason is not None)
    assert is_provider_configured(app_settings, ManagerContactChannel.SMS) is (
        reason is None
    )


def test_the_sender_carries_the_account_and_whichever_sender_is_set() -> None:
    sender = platform_sms_sender(settings(**TWILIO_ACCOUNT, **MESSAGING_SERVICE))

    assert sender is not None
    assert str(sender.account_sid) == ACCOUNT_SID
    assert sender.sender is None
    assert (
        str(sender.messaging_service_sid)
        == MESSAGING_SERVICE["TWILIO_MESSAGING_SERVICE_SID"]
    )
    assert TWILIO_ACCOUNT["TWILIO_AUTH_TOKEN"] not in repr(sender)


def test_the_sms_sender_needs_a_number_or_a_messaging_service() -> None:
    with pytest.raises(ValidationError, match=SENDER_SETTINGS):
        TwilioSmsSender(
            account_sid=TwilioAccountSid(ACCOUNT_SID),
            auth_token=PlatformSecret("fake-twilio-auth-token"),
        )


def test_staff_sms_in_production_says_the_sender_is_pending(
    caplog: pytest.LogCaptureFixture,
) -> None:
    production = ChannelsTestbed(build_settings(APP_ENV="production", **TWILIO_ACCOUNT))
    business_id = BusinessId()

    with caplog.at_level(logging.WARNING):
        queued = production.staff_notifier.notify(
            StaffNotification(
                business_id=business_id,
                contact=sms_contact(),
                text=MessageText("Handoff: a guest asks about a banquet."),
            )
        )

    [message] = outbox_of(production, business_id)
    assert queued is False
    assert message.status is OutboundMessageStatus.DEAD
    assert str(message.last_error) == MISSING_SMS_SENDER_TEXT
    # The operator's log names the missing sender; the stored reason, none.
    assert SENDER_SETTINGS in caplog.text
    assert "TWILIO_" not in MISSING_SMS_SENDER_TEXT


def test_without_any_sms_provider_the_reason_stays_the_general_one() -> None:
    production = settings("production")
    pending = settings("production", **TWILIO_ACCOUNT)
    general = MISSING_PROVIDER_TEXTS[ManagerContactChannel.SMS]

    assert str(missing_staff_provider(production, ManagerContactChannel.SMS)) == (
        general
    )
    assert str(missing_staff_provider(pending, ManagerContactChannel.SMS)) == (
        MISSING_SMS_SENDER_TEXT
    )
    # Outside production SMS without a provider is written to the log.
    assert (
        missing_staff_provider(settings(**TWILIO_ACCOUNT), ManagerContactChannel.SMS)
        is None
    )
    # Only SMS waits for a sender; the reason means nothing to another channel.
    assert str(report_missing_provider(ManagerContactChannel.SMS)) == general
    assert (
        str(
            report_missing_provider(
                ManagerContactChannel.EMAIL, SmsUnavailableReason.NO_SENDER
            )
        )
        == MISSING_PROVIDER_TEXTS[ManagerContactChannel.EMAIL]
    )


@pytest.mark.parametrize(
    ("variables", "is_reported"),
    [
        (TWILIO_ACCOUNT, True),
        ({}, False),
        ({**TWILIO_ACCOUNT, **FROM_NUMBER}, False),
    ],
)
def test_one_information_line_says_sms_is_off(
    variables: dict[str, str], is_reported: bool, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=REPORT_LOGGER):
        report_sms_sender(settings("production", **variables))

    records = [record for record in caplog.records if record.name == REPORT_LOGGER]
    assert [(record.levelno, record.getMessage()) for record in records] == (
        [(logging.INFO, SMS_OFF_MESSAGE)] if is_reported else []
    )


def test_the_start_up_checks_report_the_account_without_a_sender(
    caplog: pytest.LogCaptureFixture,
) -> None:
    container = container_with(
        {"APP_ENV": "development", "LLM_PROVIDER": "scripted", **TWILIO_ACCOUNT}
    )

    with caplog.at_level(logging.INFO, logger=REPORT_LOGGER):
        run_startup_checks(container)

    [record] = [record for record in caplog.records if record.name == REPORT_LOGGER]
    assert record.levelno == logging.INFO
    assert record.getMessage() == SMS_OFF_MESSAGE
