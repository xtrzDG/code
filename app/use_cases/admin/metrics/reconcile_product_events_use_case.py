from collections import defaultdict

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.repositories.analytics_repositories import (
    ProductEventRepoContract,
)
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.setup_repositories import ActivationEventRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.dto.analytics.product_event_drafts import ProductEventDraft
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.shared.billing_records import find_current_subscription
from app.use_cases.shared.business_walk import walk_businesses
from app.utilities.analytics.mrr_math import BILLING_EVENTS
from app.utilities.analytics.owner_journeys import first_owner
from app.utilities.analytics.reconciliation_drafts import (
    billing_corrections,
    business_drafts,
    sign_up_drafts,
)

# Sign-ups older than this are not looked at again (a year of cohorts and
# a margin); every business is, its once-only steps and billing state.
SIGN_UP_LOOKBACK_SECONDS: int = 400 * 24 * 60 * 60


class ReconcileProductEventsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Daily job: make the product events complete from the stored records.
    Sign-ups of the last 400 days, every business's creation, milestones
    (going live also from its first published version), connected channels
    and trial are recorded with the ids live recording
    gives them (a step recorded already changes nothing); where the
    replayed billing steps disagree with the stored subscription (a lost
    write, data from before analytics, a grace that ran out), one
    correcting step is recorded. The events it writes are marked as
    reconciled. Reports how many steps it looked at.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        business_repo: BusinessRepoContract,
        activation_event_repo: ActivationEventRepoContract,
        channel_repo: ChannelRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        product_event_repo: ProductEventRepoContract,
        product_events: RecordProductEventFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._activation_event_repo: ActivationEventRepoContract = activation_event_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._product_event_repo: ProductEventRepoContract = product_event_repo
        self._product_events: RecordProductEventFacilitatorContract = product_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        after_now = Microseconds(int(now) + 1)
        drafts: list[ProductEventDraft] = sign_up_drafts(
            self._user_repo.list_created_between(
                self._wall_clock.now_unix_with_delta(
                    Seconds(-SIGN_UP_LOOKBACK_SECONDS)
                ),
                after_now,
            )
        )
        billing: dict[BusinessId, list[ProductEventDocument]] = defaultdict(list)
        for event in self._product_event_repo.list_named(
            BILLING_EVENTS, None, after_now
        ):
            if event.business_id is not None:
                billing[event.business_id].append(event)

        for business in walk_businesses(self._business_repo):
            subscription: SubscriptionDocument | None = find_current_subscription(
                self._subscription_repo, business.id
            )
            drafts.extend(
                business_drafts(
                    business,
                    first_owner(business),
                    self._activation_event_repo.list_by_business(business.id),
                    self._channel_repo.list_by_business(business.id),
                    subscription,
                    self._first_published_at(business.id),
                )
            )
            if subscription is None:
                continue

            invoices: list[InvoiceDocument] = self._invoice_repo.list_by_business(
                business.id
            )
            drafts.extend(
                billing_corrections(
                    subscription, invoices, billing.get(business.id, []), now
                )
            )

        self._product_events.record(*drafts)
        return JobReport(processed_count=ProcessedItemCount(len(drafts)))

    def _first_published_at(self, business_id: BusinessId) -> Microseconds | None:
        """When the business's assistant was first published (went live)."""

        published: list[Microseconds] = [
            version.published_at
            for version in self._assistant_version_repo.list_by_business(business_id)
            if version.published_at is not None
        ]
        return min(published, key=int, default=None)
