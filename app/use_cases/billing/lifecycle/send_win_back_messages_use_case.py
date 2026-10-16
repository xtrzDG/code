"""Periodic job: the win-back messages on days 14 and 30 after a cancellation."""

import logging
from datetime import datetime

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
)
from app.contracts.repositories.subscription_event_repositories import (
    SubscriptionEventRepoContract,
)
from app.contracts.subscription_lifecycle import (
    OwnerWinBackFacilitatorContract,
    SubscriptionLifecyclePolicyRegistryContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.subscription_lifecycle import (
    SubscriptionEventKind,
    WinBackStage,
)
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.subscription_lifecycle_policy import SubscriptionLifecyclePolicy
from app.schemas.dto.win_back_messages import WinBackMessage
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    ConversationsSinceCancellation,
    WinBackRecipientCount,
)
from app.use_cases.billing.lifecycle.lifecycle_events import lifecycle_event
from app.use_cases.shared.billing_records import find_current_subscription
from app.utilities.billing.subscription_lifecycle_keys import derive_win_back_event_id
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
    to_local_moment,
)

logger: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
# Win-back messages go out in the business's daytime only.
FIRST_LOCAL_HOUR: int = 10
LAST_LOCAL_HOUR: int = 19


class SendWinBackMessagesUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Hourly job over the cancellations of the last weeks (by kind and time,
    across businesses): when a business that cancelled has not come back,
    its owners get a reason to return on day 14 and day 30, during the
    business's daytime, through the outbox (`OwnerWinBackFacilitator`):
    how many customers the assistant talked to since, that everything set
    up is kept, a hint for the reason they gave, and a link to Billing.

    Each stage goes out once per subscription (WIN_BACK_SENT, its id derived
    from the subscription and the stage); when the job was down past a
    stage, only the latest due one goes out. A business with a newer
    subscription, or one resumed since, gets nothing.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        subscription_repo: SubscriptionRepoContract,
        subscription_event_repo: SubscriptionEventRepoContract,
        conversation_repo: ConversationRepoContract,
        lifecycle_policy_registry: SubscriptionLifecyclePolicyRegistryContract,
        owner_win_back: OwnerWinBackFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._subscription_event_repo: SubscriptionEventRepoContract = (
            subscription_event_repo
        )
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._lifecycle_policy_registry: SubscriptionLifecyclePolicyRegistryContract = (
            lifecycle_policy_registry
        )
        self._owner_win_back: OwnerWinBackFacilitatorContract = owner_win_back
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        policy: SubscriptionLifecyclePolicy = self._lifecycle_policy_registry.policy()
        first_day: int = min(int(days) for days in policy.win_back_days.values())
        cancellations: list[SubscriptionEventDocument] = (
            self._subscription_event_repo.list_of_kind(
                SubscriptionEventKind.CANCELLED,
                Microseconds(
                    int(now) - int(policy.win_back_horizon_days) * MICROSECONDS_PER_DAY
                ),
                Microseconds(int(now) - first_day * MICROSECONDS_PER_DAY + 1),
            )
        )
        latest: dict[str, SubscriptionEventDocument] = {
            str(event.subscription_id): event for event in cancellations
        }
        sent: int = 0
        for cancellation in latest.values():
            try:
                sent += int(self._win_back(cancellation, policy, now))
            except Exception:
                logger.exception(
                    "The win-back of business %s failed.", cancellation.business_id
                )

        return JobReport(processed_count=ProcessedItemCount(sent))

    def _win_back(
        self,
        cancellation: SubscriptionEventDocument,
        policy: SubscriptionLifecyclePolicy,
        now: Microseconds,
    ) -> bool:
        stage: WinBackStage | None = due_stage(cancellation, policy, now)
        business: BusinessDocument | None = self._business_repo.get(
            cancellation.business_id
        )
        if stage is None or business is None or not is_daytime(business, now):
            return False

        subscription: SubscriptionDocument | None = find_current_subscription(
            self._subscription_repo, business.id
        )
        event_id = derive_win_back_event_id(cancellation.subscription_id, stage)
        if (
            subscription is None
            or subscription.id != cancellation.subscription_id
            or subscription.status is not SubscriptionStatus.CANCELLED
            or self._subscription_event_repo.get(business.id, event_id) is not None
        ):
            return False

        recipients: WinBackRecipientCount = self._owner_win_back.send(
            business,
            WinBackMessage(
                business_id=business.id,
                subscription_id=subscription.id,
                stage=stage,
                reason=cancellation.cancellation_reason,
                conversations_since=self._conversations_since(
                    business, cancellation, now
                ),
            ),
        )
        step: SubscriptionEventDocument = lifecycle_event(
            subscription, SubscriptionEventKind.WIN_BACK_SENT, now
        )
        return self._subscription_event_repo.record(
            step.model_copy(
                update={
                    "id": event_id,
                    "win_back_stage": stage,
                    "recipient_count": recipients,
                    "cancellation_reason": cancellation.cancellation_reason,
                }
            )
        )

    def _conversations_since(
        self,
        business: BusinessDocument,
        cancellation: SubscriptionEventDocument,
        now: Microseconds,
    ) -> ConversationsSinceCancellation:
        return ConversationsSinceCancellation(
            sum(
                int(mix.count)
                for mix in self._conversation_repo.count_started_by_mix(
                    business.id, cancellation.occurred_at, now
                )
            )
        )


def due_stage(
    cancellation: SubscriptionEventDocument,
    policy: SubscriptionLifecyclePolicy,
    now: Microseconds,
) -> WinBackStage | None:
    """The latest stage whose day has come (None before the first)."""

    days_since: int = (int(now) - int(cancellation.occurred_at)) // MICROSECONDS_PER_DAY
    due: list[tuple[int, WinBackStage]] = [
        (int(days), stage)
        for stage, days in policy.win_back_days.items()
        if days_since >= int(days)
    ]
    return max(due, key=lambda item: item[0])[1] if due else None


def is_daytime(business: BusinessDocument, now: Microseconds) -> bool:
    local_now: datetime = to_local_moment(
        microseconds_to_seconds(int(now)), load_time_zone(business.timezone)
    )
    return FIRST_LOCAL_HOUR <= local_now.hour < LAST_LOCAL_HOUR
