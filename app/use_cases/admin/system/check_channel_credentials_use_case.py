import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.channel_credentials import MetaTokenDebugClientContract
from app.contracts.monitoring import SystemHealthRepoContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.credential_inspection import MetaTokenFacts
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.channels.delivery_targets import decrypt_channel_secret

logger: logging.Logger = logging.getLogger(__name__)

# The channels whose credential is a Meta page or system user token.
META_CHANNEL_KINDS: tuple[ChannelKind, ...] = (
    ChannelKind.WHATSAPP,
    ChannelKind.INSTAGRAM,
    ChannelKind.MESSENGER,
)
MICROSECONDS_PER_HOUR: int = 60 * 60 * 1_000_000
# Each token is asked about about once a day (the job runs hourly).
RECHECK_AFTER_MICROSECONDS: int = 20 * MICROSECONDS_PER_HOUR
# Meta's rate limits of the app's token: a run asks about this many tokens
# at most; the rest wait for the next hour.
INSPECTIONS_PER_RUN: int = 200
CHANNELS_READ: DocumentQueryLimit = DocumentQueryLimit(10_000)


class CheckChannelCredentialsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The `check_channel_credentials` periodic job (hourly): asks Meta's
    `debug_token` about the token of every connected WhatsApp, Instagram
    and Messenger channel not asked within 20 hours (or whose stored end
    passed since it was asked: the end is confirmed within the hour), and
    stores when it runs out (`credential_expires_at`, None when it never
    does; now when Meta says it no longer works, and that moment stays
    while it keeps not working) and when it was asked
    (`credential_checked_at`). The `refresh_whatsapp_tokens` job renews the
    WhatsApp tokens of Embedded Signup before that end and tells their
    owners when it cannot; the admin system page lists the tokens that run
    out within two weeks.

    Without META_APP_ID and META_APP_SECRET there is nobody to ask: the
    run does nothing. A token Meta cannot be asked about now is tried again
    next hour; a channel reconnected meanwhile keeps its new token's
    state. Runs platform-wide (it reads every business's channels).
    """

    def __init__(
        self,
        system_health_repo: SystemHealthRepoContract,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        token_client: MetaTokenDebugClientContract,
        meta_app_id: PlatformIdentifier | None,
        meta_app_secret: PlatformSecret | None,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._health: SystemHealthRepoContract = system_health_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._token_client: MetaTokenDebugClientContract = token_client
        self._app_id: PlatformIdentifier | None = meta_app_id
        self._app_secret: PlatformSecret | None = meta_app_secret
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        if self._app_id is None or self._app_secret is None:
            logger.info(
                "Meta token check skipped: META_APP_ID and META_APP_SECRET are not set"
            )
            return JobReport()

        now: Microseconds = self._wall_clock.now_unix()
        due: list[ChannelDocument] = [
            channel
            for channel in self._health.list_active_channels(
                META_CHANNEL_KINDS, CHANNELS_READ
            )
            if channel.encrypted_secret is not None and is_due(channel, now)
        ]
        checked: int = 0
        for channel in due[:INSPECTIONS_PER_RUN]:
            if self._check(channel, self._app_id, self._app_secret, now):
                checked += 1

        if len(due) > INSPECTIONS_PER_RUN:
            logger.info(
                "Meta token check: %d of %d due tokens asked; the rest next hour",
                INSPECTIONS_PER_RUN,
                len(due),
            )
        return JobReport(processed_count=ProcessedItemCount(checked))

    def _check(
        self,
        channel: ChannelDocument,
        app_id: PlatformIdentifier,
        app_secret: PlatformSecret,
        now: Microseconds,
    ) -> bool:
        try:
            token = decrypt_channel_secret(channel, self._secret_cipher)
            if token is None:
                return False

            facts: MetaTokenFacts = self._token_client.inspect_token(
                token, app_id, app_secret
            )
        except ApplicationError as error:
            logger.warning(
                "Meta token check of channel %s failed: %s", channel.id, error
            )
            return False

        def record(stored: ChannelDocument) -> ChannelDocument | None:
            if stored.encrypted_secret != channel.encrypted_secret:
                return None  # Reconnected meanwhile: another token.

            return stored.model_copy(
                update={
                    "credential_expires_at": credential_end(
                        facts, now, stored.credential_expires_at
                    ),
                    "credential_checked_at": now,
                }
            )

        stored = self._channel_repo.modify(channel.business_id, channel.id, record)
        return stored is not None


def is_due(channel: ChannelDocument, now: Microseconds) -> bool:
    """
    Never asked, asked more than 20 hours ago, or its stored end passed
    since it was asked (whether it really ended is known within the hour).
    """

    checked_at: Microseconds | None = channel.credential_checked_at
    if checked_at is None or int(now) - int(checked_at) > RECHECK_AFTER_MICROSECONDS:
        return True

    ends_at: Microseconds | None = channel.credential_expires_at
    return ends_at is not None and int(checked_at) < int(ends_at) <= int(now)


def credential_end(
    facts: MetaTokenFacts,
    now: Microseconds,
    stored_end: Microseconds | None,
) -> Microseconds | None:
    """
    When the token stops working: its end, or when it already stopped. A
    token that no longer works keeps the stored end once that has passed,
    so the moment it ended stays the same at every check.
    """

    if facts.is_valid:
        return facts.expires_at

    if stored_end is not None and int(stored_end) <= int(now):
        return stored_end

    if facts.expires_at is not None and int(facts.expires_at) < int(now):
        return facts.expires_at

    return now
