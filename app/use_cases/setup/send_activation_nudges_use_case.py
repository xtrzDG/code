"""Periodic job: the activation nudges that bring stuck owners back."""

import logging
from datetime import datetime

from typed_time_provider import Microseconds, WallClock

from app.contracts.nudges import OwnerNudgeFacilitatorContract
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.setup_repositories import (
    ActivationEventRepoContract,
    NudgeSentRepoContract,
    SetupStateRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.setup import ActivationEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import NudgeSentDocument, SetupStateDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.setup.nudges import NudgeMessage
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.setup.constrained_integers import NudgeRecipientCount
from app.use_cases.shared.business_walk import walk_businesses
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
    to_local_moment,
)
from app.utilities.setup.guide_views import count_customer_channels
from app.utilities.setup.nudge_schedule import (
    MICROSECONDS_PER_DAY,
    NudgeRule,
    NudgeSituation,
    due_nudge,
    nudge_topic,
)
from app.utilities.setup.setup_keys import derive_nudge_sent_id

logger: logging.Logger = logging.getLogger(__name__)
# Older businesses get no nudges: nothing is due past the last rule's grace.
NUDGE_HORIZON_DAYS: int = 12


class SendActivationNudgesUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Hourly job over every business: the activation nudge due now, if any
    (`nudge_schedule.py`: days 1, 3 and 7 without going live; days 2 and 5
    after going live without a second channel or a first real
    conversation; day 10 without a printed QR code or a hosted page
    visit), sent to the owners by e-mail, Telegram and on their devices
    during the business's daytime.

    Each nudge goes out once per business: `nudges_sent` is keyed by the
    business and the nudge, so a run after a restart or on another worker
    finds it and moves on, and the outbox queues each address once, so a
    run that died between queueing and recording queues nothing twice.
    Businesses whose owners turned the reminders off, paused businesses
    and businesses older than the schedule are skipped; one failing
    business never stops the others.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        activation_event_repo: ActivationEventRepoContract,
        setup_state_repo: SetupStateRepoContract,
        nudge_sent_repo: NudgeSentRepoContract,
        owner_nudges: OwnerNudgeFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._activation_event_repo: ActivationEventRepoContract = activation_event_repo
        self._setup_state_repo: SetupStateRepoContract = setup_state_repo
        self._nudge_sent_repo: NudgeSentRepoContract = nudge_sent_repo
        self._owner_nudges: OwnerNudgeFacilitatorContract = owner_nudges
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        sent: int = 0
        now: Microseconds = self._wall_clock.now_unix()
        for business in walk_businesses(self._business_repo):
            try:
                sent += int(self._nudge(business, now))
            except Exception:
                logger.exception("Nudges of business %s failed.", business.id)

        return JobReport(processed_count=ProcessedItemCount(sent))

    def _nudge(self, business: BusinessDocument, now: Microseconds) -> bool:
        state: SetupStateDocument | None = self._setup_state_repo.get_by_business(
            business.id
        )
        if (state is not None and state.reminders_off_at is not None) or (
            business.status is BusinessStatus.PAUSED
        ):
            return False

        situation: NudgeSituation | None = self._situation(business, state, now)
        if situation is None:
            return False

        local_now: datetime = to_local_moment(
            microseconds_to_seconds(int(now)), load_time_zone(business.timezone)
        )
        rule: NudgeRule | None = due_nudge(situation, now, local_now)
        if rule is None or self._nudge_sent_repo.find(business.id, rule.code):
            return False

        recipients: NudgeRecipientCount = self._owner_nudges.send(
            business,
            NudgeMessage(
                business_id=business.id,
                code=rule.code,
                topic=nudge_topic(rule.code, situation),
            ),
        )
        return self._nudge_sent_repo.record_once(
            NudgeSentDocument(
                id=derive_nudge_sent_id(business.id, rule.code),
                business_id=business.id,
                code=rule.code,
                recipient_count=recipients,
                sent_at=now,
                created_at=now,
                updated_at=now,
            )
        )

    def _situation(
        self,
        business: BusinessDocument,
        state: SetupStateDocument | None,
        now: Microseconds,
    ) -> NudgeSituation | None:
        horizon: int = int(now) - NUDGE_HORIZON_DAYS * MICROSECONDS_PER_DAY
        kinds: dict[ActivationEventKind, Microseconds] = {
            event.kind: event.occurred_at
            for event in self._activation_event_repo.list_by_business(business.id)
        }
        went_live_at: Microseconds | None = kinds.get(ActivationEventKind.WENT_LIVE)
        if went_live_at is None and business.published_assistant_version_id:
            # Live before milestones were recorded: no launch date to count from.
            return None

        anchor: int = int(business.created_at if went_live_at is None else went_live_at)
        if anchor < horizon:
            return None

        return NudgeSituation(
            created_at=business.created_at,
            went_live_at=went_live_at,
            is_answering=business.status is BusinessStatus.LIVE,
            customer_channel_count=count_customer_channels(
                self._channel_repo.list_by_business(business.id)
            ),
            has_first_conversation=ActivationEventKind.FIRST_CONVERSATION in kinds,
            has_shared=state is not None
            and (
                state.shared_at is not None or state.hosted_page_visited_at is not None
            ),
        )
