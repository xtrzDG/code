from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    RetentionOfferKind,
    SubscriptionEventKind,
    WinBackStage,
)
from app.schemas.typings.billing.prefixed_id import SubscriptionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    PauseMonthCount,
    WinBackRecipientCount,
)
from app.schemas.typings.subscription_lifecycle.constrained_strings import (
    CancellationDetails,
)
from app.schemas.typings.subscription_lifecycle.prefixed_id import (
    SubscriptionEventId,
)
from app.schemas.typings.users.prefixed_id import UserId


class SubscriptionEventDocument(BaseDocument):
    """
    One step of a subscription's life (`subscription_events`, migration
    1161), a business collection read per business and, by kind and time,
    across businesses for the founder's churn metrics:

    - CANCELLED: the owner's `cancellation_reason` and `details` in their
      own words, and the offer the dialog showed that they turned down
      (`offer_kind`);
    - OFFER_ACCEPTED: the offer taken instead (`offer_kind`) and the reason
      that brought it;
    - PAUSE_SCHEDULED, PAUSE_STARTED and RESUMED: the pause they belong to
      (`pause_starts_at`, `pause_until`, `pause_months`); a RESUMED step
      before the pause started calls it off, one during the pause ends it
      early (its `occurred_at`);
    - WIN_BACK_SENT: the `win_back_stage` and how many addresses it was
      queued for; its id derives from the subscription and the stage, so a
      stage is sent once.

    `actor_id` is the owner who acted; None for the platform's jobs.
    """

    id: SubscriptionEventId = Field(default_factory=SubscriptionEventId)
    business_id: BusinessId
    subscription_id: SubscriptionId
    kind: SubscriptionEventKind
    occurred_at: Microseconds
    actor_id: UserId | None = None
    cancellation_reason: CancellationReason | None = None
    details: CancellationDetails | None = None
    offer_kind: RetentionOfferKind | None = None
    pause_starts_at: Microseconds | None = None
    pause_until: Microseconds | None = None
    pause_months: PauseMonthCount | None = None
    win_back_stage: WinBackStage | None = None
    recipient_count: WinBackRecipientCount | None = None
