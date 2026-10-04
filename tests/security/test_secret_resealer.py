"""
Re-sealing one business's secrets: what a run counts when secrets change
under it, a webhook cannot be registered again or a token needs no work.
"""

from collections.abc import Callable

import pytest
from typed_time_provider import Microseconds

from app.adapters.security.secret_cipher_adapter import SecretCipherAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.channel_clients import ProviderToken, TelegramBotApiClientContract
from app.repositories.business_repositories import ChannelRepository
from app.repositories.calendar_repositories import CalendarConnectionRepository
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.calendar import CalendarConnectionDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.provider_profiles import TelegramBotProfile
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.bookings.strings import ExternalCalendarId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    ChannelWebhookUrl,
    TelegramBotUserId,
    TelegramWebhookSecret,
)
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
    OutboundMessagePart,
    ProviderMessageId,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.media.strings import ProviderMediaId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.security.secret_resealer import RotationTally, SecretResealer
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)

OLD_KEY: str = "resealer-old-encryption-key-0123456789ab"  # gitleaks:allow
NEW_KEY: str = "resealer-new-encryption-key-fedcba987654"  # gitleaks:allow
BOT_TOKEN: ChannelSecret = ChannelSecret("123456:bot-token")
BUSINESS: BusinessId = BusinessId()
OLD = SecretCipherAdapter(assemble_app_settings({"ENCRYPTION_KEYS": OLD_KEY}))


class RecordingTelegram(TelegramBotApiClientContract):
    def __init__(self, failure: ExternalServiceError | None = None) -> None:
        self.webhooks: list[tuple[str, str]] = []
        self.failure: ExternalServiceError | None = failure

    def get_me(self, bot_token: ProviderToken) -> TelegramBotProfile:
        raise NotImplementedError

    def set_webhook(
        self,
        bot_token: ProviderToken,
        url: ChannelWebhookUrl,
        secret_token: TelegramWebhookSecret,
    ) -> None:
        if self.failure is not None:
            raise self.failure
        self.webhooks.append((str(bot_token), str(url)))

    def delete_webhook(self, bot_token: ProviderToken) -> None:
        raise NotImplementedError

    def send_message(
        self,
        bot_token: ProviderToken,
        chat_id: ChannelUserId,
        text: OutboundMessagePart,
    ) -> ProviderMessageId | None:
        raise NotImplementedError

    def send_typing_action(
        self, bot_token: ProviderToken, chat_id: ChannelUserId
    ) -> None:
        raise NotImplementedError

    def get_profile_photo_file_id(
        self, bot_token: ProviderToken, bot_user_id: TelegramBotUserId
    ) -> ProviderMediaId | None:
        raise NotImplementedError


class RacingChannelRepository(ChannelRepository):
    """The owner reconnects the channel just before the run writes it."""

    def modify(
        self,
        business_id: BusinessId,
        channel_id: ChannelId,
        change: Callable[[ChannelDocument], ChannelDocument | None],
    ) -> ChannelDocument | None:
        stored = self.get(channel_id)
        assert stored is not None
        reconnected = ring().encrypt(ChannelSecret("654321:new-bot-token"))
        self.save(stored.model_copy(update={"encrypted_secret": reconnected}))
        return super().modify(business_id, channel_id, change)


class RacingCalendarRepository(CalendarConnectionRepository):
    """Google refreshes the access token just before the run writes it."""

    def modify(
        self,
        business_id: BusinessId,
        change: Callable[
            [CalendarConnectionDocument], CalendarConnectionDocument | None
        ],
    ) -> CalendarConnectionDocument | None:
        stored = self.get_by_business(business_id)
        assert stored is not None
        refreshed = ring().encrypt(ChannelSecret("ya29.refreshed"))
        self.save(stored.model_copy(update={"encrypted_access_token": refreshed}))
        return super().modify(business_id, change)


def ring() -> SecretCipherAdapter:
    return SecretCipherAdapter(
        assemble_app_settings({"ENCRYPTION_KEYS": f"{NEW_KEY},{OLD_KEY}"})
    )


def channel(kind: ChannelKind, secret: ChannelSecret | None) -> ChannelDocument:
    return ChannelDocument(
        business_id=BUSINESS,
        kind=kind,
        external_id=ChannelExternalId(f"{kind.value}-1"),
        encrypted_secret=None if secret is None else OLD.encrypt(secret),
        status=ChannelStatus.CONNECTED,
        created_at=Microseconds(1),
        updated_at=Microseconds(1),
    )


def calendar(access_token: ChannelSecret | None) -> CalendarConnectionDocument:
    return CalendarConnectionDocument(
        business_id=BUSINESS,
        calendar_id=ExternalCalendarId("primary"),
        encrypted_refresh_token=OLD.encrypt(ChannelSecret("1//refresh")),
        encrypted_access_token=None
        if access_token is None
        else OLD.encrypt(access_token),
        connected_by=UserId(),
        created_at=Microseconds(1),
        updated_at=Microseconds(1),
    )


def resealer(
    channels: ChannelRepository,
    calendars: CalendarConnectionRepository,
    telegram: RecordingTelegram,
    environment: dict[str, str] | None = None,
) -> SecretResealer:
    settings = assemble_app_settings(
        environment
        or {
            "ENCRYPTION_KEYS": f"{NEW_KEY},{OLD_KEY}",
            "APP_BASE_URL": "https://api.example.com",
        }
    )
    return SecretResealer(
        channel_repo=channels,
        calendar_connection_repo=calendars,
        secret_cipher=SecretCipherAdapter(settings),
        secret_rotation=SecretCipherAdapter(settings),
        telegram_client=telegram,
        app_settings=settings,
    )


def channel_repo(
    kind: type[ChannelRepository] = ChannelRepository,
) -> ChannelRepository:
    return kind(InMemoryDocumentCollectionAdapter[ChannelDocument](ChannelDocument))


def calendar_repo(
    kind: type[CalendarConnectionRepository] = CalendarConnectionRepository,
) -> CalendarConnectionRepository:
    return kind(
        InMemoryDocumentCollectionAdapter[CalendarConnectionDocument](
            CalendarConnectionDocument
        )
    )


def test_a_reconnect_during_the_run_is_kept_and_counted_as_current() -> None:
    channels = channel_repo(RacingChannelRepository)
    stored = channel(ChannelKind.TELEGRAM, BOT_TOKEN)
    channels.save(channel(ChannelKind.WHATSAPP, None))
    channels.save(stored)
    tally = RotationTally()

    resealer(channels, calendar_repo(), RecordingTelegram()).reseal_business(
        BUSINESS, tally
    )

    after = channels.get(stored.id)
    assert after is not None and after.encrypted_secret is not None
    assert str(ring().decrypt(after.encrypted_secret)) == "654321:new-bot-token"
    assert (tally.total, tally.current, tally.rotated) == (1, 1, 0)


@pytest.mark.parametrize(
    ("environment", "failure"),
    [
        ({"ENCRYPTION_KEYS": f"{NEW_KEY},{OLD_KEY}"}, None),
        (None, ExternalServiceError("Telegram is down.")),
    ],
    ids=["without APP_BASE_URL", "Telegram refuses"],
)
def test_a_webhook_that_cannot_be_registered_again_is_counted(
    environment: dict[str, str] | None, failure: ExternalServiceError | None
) -> None:
    channels = channel_repo()
    channels.save(channel(ChannelKind.TELEGRAM, BOT_TOKEN))
    telegram = RecordingTelegram(failure)
    tally = RotationTally()

    resealer(channels, calendar_repo(), telegram, environment).reseal_business(
        BUSINESS, tally
    )

    assert (tally.rotated, tally.webhooks_renewed, tally.webhooks_failed) == (1, 0, 1)
    assert telegram.webhooks == []


def test_a_calendar_without_an_access_token_or_already_current_is_left_alone() -> None:
    calendars = calendar_repo()
    calendars.save(calendar(None))
    service = resealer(channel_repo(), calendars, RecordingTelegram())
    first, second = RotationTally(), RotationTally()

    service.reseal_business(BUSINESS, first)
    service.reseal_business(BUSINESS, second)

    assert (first.total, first.rotated) == (1, 1)
    assert (second.total, second.current, second.rotated) == (1, 1, 0)
    stored = calendars.get_by_business(BUSINESS)
    assert stored is not None and stored.encrypted_access_token is None


def test_a_calendar_refreshed_during_the_run_is_kept_and_counted_as_current() -> None:
    calendars = calendar_repo(RacingCalendarRepository)
    calendars.save(calendar(ChannelSecret("ya29.old")))
    tally = RotationTally()

    resealer(channel_repo(), calendars, RecordingTelegram()).reseal_business(
        BUSINESS, tally
    )

    stored = calendars.get_by_business(BUSINESS)
    assert stored is not None and stored.encrypted_access_token is not None
    assert str(ring().decrypt(stored.encrypted_access_token)) == "ya29.refreshed"
    assert (tally.total, tally.current, tally.rotated) == (2, 2, 0)
