"""
A `send_platform_alert` job sends one message through the staff providers
(retried by the queue when the provider fails, ended when there is none),
and PLATFORM_ALERT_* configure where the alerts go.
"""

from collections.abc import Sequence

import pytest

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.outbound_messages import OutboundTemplate
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.dto.platform_alerts import PlatformAlertDelivery
from app.schemas.exceptions.application_errors import (
    DeliveryNotConfiguredError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress
from app.schemas.typings.monitoring.strings import PlatformAlertMessage
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.use_cases.admin.alerts.check_platform_alerts_use_case import (
    SEND_PLATFORM_ALERT_JOB,
)
from app.use_cases.admin.alerts.send_platform_alert_use_case import (
    SendPlatformAlertUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)

ALERT: str = "[SEV1] FIRING: Model errors\nSome model calls failed."
BASE_ENVIRONMENT: dict[str, str] = {"APP_ENV": "test"}


class RecordingSender:
    """Staff providers that split in two and fail as told."""

    def __init__(self, error: Exception | None = None) -> None:
        self.sent: list[tuple[ManagerContact, str]] = []
        self._error: Exception | None = error

    def split(self, contact: ManagerContact, text: MessageText) -> list[MessageText]:
        del contact
        first, rest = str(text).split("\n", 1)
        return [MessageText(first), MessageText(rest)]

    def send(
        self,
        contact: ManagerContact,
        text: MessageText,
        template: OutboundTemplate | None,
    ) -> ProviderMessageId | None:
        assert template is None
        if self._error is not None:
            raise self._error
        self.sent.append((contact, str(text)))
        return None

    def send_with_files(
        self,
        contact: ManagerContact,
        text: MessageText,
        attachments: Sequence[EmailAttachment],
    ) -> None:
        raise AssertionError("Platform alerts carry no files.")


def queued(channel: ManagerContactChannel, address: str) -> QueuedJobInput:
    delivery = PlatformAlertDelivery(
        channel=channel,
        address=ManagerContactAddress(address),
        text=PlatformAlertMessage(ALERT),
    )
    return QueuedJobInput(
        job_id=QueuedJobId(),
        job_name=JobName(str(SEND_PLATFORM_ALERT_JOB)),
        payload=JobPayloadJson(delivery.model_dump_json()),
    )


def test_an_alert_goes_to_its_recipient_in_the_parts_the_channel_needs() -> None:
    sender = RecordingSender()

    report = SendPlatformAlertUseCase(sender).run(
        queued(ManagerContactChannel.TELEGRAM, "-1001234567890")
    )

    assert int(report.processed_count) == 2
    [(contact, first), (_, second)] = sender.sent
    assert contact.channel is ManagerContactChannel.TELEGRAM
    assert str(contact.address) == "-1001234567890"
    assert str(contact.language) == "en"
    assert (first, second) == (
        "[SEV1] FIRING: Model errors",
        "Some model calls failed.",
    )


def test_a_provider_failure_is_raised_for_the_queue_to_retry() -> None:
    sender = RecordingSender(ExternalServiceError("Telegram is down."))

    with pytest.raises(ExternalServiceError):
        SendPlatformAlertUseCase(sender).run(
            queued(ManagerContactChannel.EMAIL, "oncall@workshop.example")
        )


def test_without_a_provider_the_job_ends() -> None:
    sender = RecordingSender(DeliveryNotConfiguredError("No platform bot token."))

    report = SendPlatformAlertUseCase(sender).run(
        queued(ManagerContactChannel.TELEGRAM, "-1001234567890")
    )

    assert int(report.processed_count) == 0


def test_the_alert_recipients_and_cooldown_come_from_the_environment() -> None:
    settings = assemble_app_settings(
        {
            **BASE_ENVIRONMENT,
            "PLATFORM_ALERT_TELEGRAM_CHAT_IDS": "-1001234567890, 424242",
            "PLATFORM_ALERT_EMAILS": "OnCall@Workshop.example",
            "PLATFORM_ALERT_COOLDOWN_MINUTES": "30",
        }
    ).platform_alerts

    assert [str(chat) for chat in settings.telegram_chat_ids] == [
        "-1001234567890",
        "424242",
    ]
    assert [str(email) for email in settings.emails] == ["oncall@workshop.example"]
    assert int(settings.cooldown_minutes) == 30


def test_by_default_alerts_are_only_logged_and_repeat_hourly() -> None:
    settings = assemble_app_settings(BASE_ENVIRONMENT).platform_alerts

    assert settings.telegram_chat_ids == [] and settings.emails == []
    assert int(settings.cooldown_minutes) == 60


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("PLATFORM_ALERT_TELEGRAM_CHAT_IDS", "@oncall"),
        ("PLATFORM_ALERT_EMAILS", "not-an-address"),
        ("PLATFORM_ALERT_COOLDOWN_MINUTES", "1"),
        ("PLATFORM_ALERT_COOLDOWN_MINUTES", "2000"),
    ],
)
def test_invalid_alert_settings_are_refused(name: str, value: str) -> None:
    with pytest.raises(ValidationFailedError, match=name):
        assemble_app_settings({**BASE_ENVIRONMENT, name: value})
