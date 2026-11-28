import logging
from collections import Counter
from dataclasses import dataclass, field

from typed_time_provider import Microseconds, WallClock

from app.contracts.channel_credentials import ChannelCredentialWatchRepoContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.deliveries import DeliveryFailureReason
from app.schemas.constants.meta_connection import (
    WhatsAppTokenNoticeStage,
    WhatsAppTokenRefreshOutcome,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.meta_provider import MetaAppCredentials
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.channels.meta_connection.whatsapp_token_notices import (
    WhatsAppTokenNotices,
)
from app.use_cases.channels.meta_connection.whatsapp_token_refresh import (
    WhatsAppTokenRefresh,
)
from app.utilities.channels.channel_health import (
    is_channel_active,
    mark_channel_failing,
    reload_same_connection,
)
from app.utilities.channels.meta_sign_in import meta_app_of
from app.utilities.channels.whatsapp_token_schedule import (
    CHANNELS_READ,
    REFRESHES_PER_RUN,
    has_token_ended,
    notice_stage,
    refresh_window,
)

logger: logging.Logger = logging.getLogger(__name__)
# The platform's words on the Channels page for a token that ended.
TOKEN_ENDED_ERROR: str = "The access token Meta issued for this number has expired."


@dataclass
class RefreshTally:
    """What one run did, for its log line."""

    outcomes: Counter[WhatsAppTokenRefreshOutcome] = field(
        default_factory=Counter[WhatsAppTokenRefreshOutcome]
    )
    ended: int = 0
    notices: int = 0
    failed: int = 0
    waiting: int = 0


class RefreshWhatsAppTokensUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The `refresh_whatsapp_tokens` periodic job (every 6 hours,
    platform-wide): the business's own WhatsApp token of Embedded Signup
    runs 60 days, so the platform renews it before its end
    (META_TOKEN_REFRESH_DAYS, 15 by default) and tells the owners when
    that fails.

    It acts on what the hourly `check_channel_credentials` stored: the
    connected WhatsApp channels (and those in ERROR) holding a token of
    their own whose end falls within the refresh window, soonest first, at
    most REFRESHES_PER_RUN renewals a run (the rest wait for the next
    one), and those whose token already ended: on a connected channel
    however long ago (one switched back on, as when a business closure is
    cancelled weeks later), on one already in ERROR within the last week
    (it was handled then). A number connected by hand (sent with the
    platform's token), Instagram, Messenger and switched-off channels are
    left alone.

    - A token that ended needs no Meta call: the channel is put in ERROR as
      a refused credential (the Channels page offers "Connect again", the
      inbox counts it, `channel.error` is announced) unless it is already
      there, and the owners get the urgent ENDED reminder.
    - Any other token is renewed (`WhatsAppTokenRefresh`). Meta refused:
      the owners are told (REFRESH_REFUSED, or ENDING with three days or
      less left); Meta could not be asked: the next run tries again, and
      the owners hear only when three days or less remain (ENDING).

    Each reminder reaches each recipient once per token and stage, however
    often the run sees the token. Without META_APP_ID and META_APP_SECRET
    the run does nothing. One channel's failure never stops the others;
    one log line tells what the run did. `processed_count` counts the
    renewed tokens and the reminders.
    """

    def __init__(
        self,
        credential_watch: ChannelCredentialWatchRepoContract,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        live_events: EventPublisherFacilitatorContract,
        token_refresh: WhatsAppTokenRefresh,
        notices: WhatsAppTokenNotices,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._credential_watch: ChannelCredentialWatchRepoContract = credential_watch
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._token_refresh: WhatsAppTokenRefresh = token_refresh
        self._notices: WhatsAppTokenNotices = notices
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        app: MetaAppCredentials | None = meta_app_of(self._app_settings)
        if app is None:
            logger.info(
                "WhatsApp token refresh skipped: META_APP_ID and META_APP_SECRET "
                "are not set"
            )
            return JobReport()

        now: Microseconds = self._wall_clock.now_unix()
        in_error_ending_from, ending_before = refresh_window(
            now, self._app_settings.meta_token_refresh_days
        )
        tally = RefreshTally()
        for channel in self._credential_watch.list_active_credentials_ending_before(
            ChannelKind.WHATSAPP, ending_before, in_error_ending_from, CHANNELS_READ
        ):
            try:
                self._handle(channel, app, now, tally)
            except ApplicationError as error:
                tally.failed += 1
                logger.warning(
                    "WhatsApp token refresh of channel %s failed: %s", channel.id, error
                )

        outcomes = tally.outcomes
        logger.info(
            "WhatsApp token refresh: %d renewed, %d refused, %d deferred, "
            "%d replaced, %d ended, %d reminders, %d failed, %d left for the "
            "next run",
            outcomes[WhatsAppTokenRefreshOutcome.REFRESHED],
            outcomes[WhatsAppTokenRefreshOutcome.REFUSED],
            outcomes[WhatsAppTokenRefreshOutcome.DEFERRED],
            outcomes[WhatsAppTokenRefreshOutcome.REPLACED],
            tally.ended,
            tally.notices,
            tally.failed,
            tally.waiting,
        )
        return JobReport(
            processed_count=ProcessedItemCount(
                outcomes[WhatsAppTokenRefreshOutcome.REFRESHED] + tally.notices
            )
        )

    def _handle(
        self,
        channel: ChannelDocument,
        app: MetaAppCredentials,
        now: Microseconds,
        tally: RefreshTally,
    ) -> None:
        ends_at: Microseconds | None = channel.credential_expires_at
        if channel.encrypted_secret is None or ends_at is None:
            return  # Connected by hand: sent with the platform's token.

        if has_token_ended(channel, now):
            self._end(channel, now, tally)
            return

        if tally.outcomes.total() >= REFRESHES_PER_RUN:
            tally.waiting += 1
            return

        outcome = self._token_refresh.refresh(channel, app, now)
        tally.outcomes[outcome] += 1
        stage: WhatsAppTokenNoticeStage | None = notice_stage(ends_at, now, outcome)
        if stage is None:
            return

        current: ChannelDocument | None = self._still_holding(channel)
        if current is not None:
            self._notify(current, stage, tally)

    def _end(
        self, channel: ChannelDocument, now: Microseconds, tally: RefreshTally
    ) -> None:
        current: ChannelDocument | None = self._still_holding(channel)
        if current is None or not has_token_ended(current, now):
            return  # Replaced, switched off or found working meanwhile.

        tally.ended += 1
        if (
            current.status is not ChannelStatus.ERROR
            or current.last_error_reason
            is not DeliveryFailureReason.CREDENTIAL_REJECTED
        ):
            mark_channel_failing(
                self._channel_repo,
                self._live_events,
                current,
                TOKEN_ENDED_ERROR,
                now,
                DeliveryFailureReason.CREDENTIAL_REJECTED,
            )
        self._notify(current, WhatsAppTokenNoticeStage.ENDED, tally)

    def _still_holding(self, channel: ChannelDocument) -> ChannelDocument | None:
        """The channel as stored, while it is on with the token it was read with."""

        current: ChannelDocument | None = reload_same_connection(
            self._channel_repo, channel
        )
        if current is None or not is_channel_active(current):
            return None

        return current

    def _notify(
        self,
        channel: ChannelDocument,
        stage: WhatsAppTokenNoticeStage,
        tally: RefreshTally,
    ) -> None:
        business: BusinessDocument | None = self._business_repo.get(channel.business_id)
        if business is None:
            return

        self._notices.notify(business, channel, stage)
        tally.notices += 1
