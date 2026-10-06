from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.client_care_repositories import (
    BillingCreditRepoContract,
)
from app.contracts.repositories.subscription_event_repositories import (
    SubscriptionEventRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import BillingCreditKind
from app.schemas.constants.subscription_lifecycle import (
    RetentionOfferKind,
    SubscriptionEventKind,
)
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    BillingOverviewSource,
    ChangePlanCommand,
    ChangePlanRequest,
)
from app.schemas.dto.subscription_lifecycle import (
    AcceptRetentionOfferCommand,
    PauseSubscriptionCommand,
    PauseSubscriptionRequest,
    RetentionOfferView,
    SubscriptionLifecycleView,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import BillingCreditAmountMinor
from app.use_cases.billing.lifecycle.lifecycle_events import lifecycle_event
from app.use_cases.shared.billing_records import require_current_subscription
from app.utilities.billing.subscription_lifecycle_keys import derive_save_credit_id


class AcceptRetentionOfferUseCase(
    UseCaseContract[AcceptRetentionOfferCommand, BillingOverview]
):
    """
    POST /v1/businesses/{business_id}/billing/offers/accept: instead of
    cancelling, the owner takes the offer the cancel dialog made for the
    reason they chose, as the server works it out again now (the cabinet
    cannot name its own price):

    - PAUSE: the seasonal pause for the months chosen (`PauseSubscriptionUseCase`);
    - DOWNGRADE: the next cheaper plan, same billing period (`ChangePlanUseCase`);
    - CREDIT: the one-time credit on the ledger (`billing_credits`, once per
      business), used by the next invoices before tax.

    The step is recorded (OFFER_ACCEPTED with the reason). Refused (409)
    when the offer is not the one the reason gets now.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        assemble_subscription_lifecycle: UseCaseContract[
            BillingOverviewSource, SubscriptionLifecycleView
        ],
        pause_subscription: UseCaseContract[PauseSubscriptionCommand, BillingOverview],
        change_plan: UseCaseContract[ChangePlanCommand, BillingOverview],
        assemble_billing_overview: UseCaseContract[
            BillingOverviewSource, BillingOverview
        ],
        subscription_repo: SubscriptionRepoContract,
        billing_credit_repo: BillingCreditRepoContract,
        subscription_event_repo: SubscriptionEventRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._assemble_subscription_lifecycle: UseCaseContract[
            BillingOverviewSource, SubscriptionLifecycleView
        ] = assemble_subscription_lifecycle
        self._pause_subscription: UseCaseContract[
            PauseSubscriptionCommand, BillingOverview
        ] = pause_subscription
        self._change_plan: UseCaseContract[ChangePlanCommand, BillingOverview] = (
            change_plan
        )
        self._assemble_billing_overview: UseCaseContract[
            BillingOverviewSource, BillingOverview
        ] = assemble_billing_overview
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._billing_credit_repo: BillingCreditRepoContract = billing_credit_repo
        self._subscription_event_repo: SubscriptionEventRepoContract = (
            subscription_event_repo
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AcceptRetentionOfferCommand) -> BillingOverview:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        source = BillingOverviewSource(
            business=business, display_language=input_data.display_language
        )
        offer: RetentionOfferView = self._offer(source, input_data)
        overview: BillingOverview = self._apply(business, source, offer, input_data)
        subscription: SubscriptionDocument = require_current_subscription(
            self._subscription_repo, business.id
        )
        accepted: SubscriptionEventDocument = lifecycle_event(
            subscription,
            SubscriptionEventKind.OFFER_ACCEPTED,
            self._wall_clock.now_unix(),
            input_data.user_id,
        )
        self._subscription_event_repo.record(
            accepted.model_copy(
                update={
                    "cancellation_reason": input_data.request.reason,
                    "offer_kind": offer.kind,
                    "pause_months": input_data.request.pause_months,
                }
            )
        )
        return overview

    def _offer(
        self, source: BillingOverviewSource, input_data: AcceptRetentionOfferCommand
    ) -> RetentionOfferView:
        lifecycle: SubscriptionLifecycleView = (
            self._assemble_subscription_lifecycle.run(source)
        )
        for choice in lifecycle.offers:
            if (
                choice.reason is input_data.request.reason
                and choice.offer is not None
                and choice.offer.kind is input_data.request.kind
            ):
                return choice.offer

        raise ConflictError("This offer is not available for the reason given.")

    def _apply(
        self,
        business: BusinessDocument,
        source: BillingOverviewSource,
        offer: RetentionOfferView,
        input_data: AcceptRetentionOfferCommand,
    ) -> BillingOverview:
        match offer.kind:
            case RetentionOfferKind.PAUSE:
                if input_data.request.pause_months is None:
                    raise ValidationFailedError("Say how many months to pause.")

                return self._pause_subscription.run(
                    PauseSubscriptionCommand(
                        user_id=input_data.user_id,
                        business_id=business.id,
                        request=PauseSubscriptionRequest(
                            months=input_data.request.pause_months
                        ),
                        display_language=input_data.display_language,
                    )
                )
            case RetentionOfferKind.DOWNGRADE:
                return self._downgrade(business, offer, input_data)
            case RetentionOfferKind.CREDIT:
                self._grant_credit(business, offer)
                return self._assemble_billing_overview.run(source)

    def _downgrade(
        self,
        business: BusinessDocument,
        offer: RetentionOfferView,
        input_data: AcceptRetentionOfferCommand,
    ) -> BillingOverview:
        subscription: SubscriptionDocument = require_current_subscription(
            self._subscription_repo, business.id
        )
        if offer.plan_key is None:
            raise ConflictError("There is no cheaper plan to move to.")

        return self._change_plan.run(
            ChangePlanCommand(
                user_id=input_data.user_id,
                business_id=business.id,
                request=ChangePlanRequest(
                    plan_key=offer.plan_key,
                    billing_period=subscription.billing_period,
                ),
                display_language=input_data.display_language,
            )
        )

    def _grant_credit(
        self, business: BusinessDocument, offer: RetentionOfferView
    ) -> None:
        subscription: SubscriptionDocument = require_current_subscription(
            self._subscription_repo, business.id
        )
        if offer.credit is None:
            raise ConflictError("There is no credit to give.")

        now: Microseconds = self._wall_clock.now_unix()
        is_granted: bool = self._billing_credit_repo.record(
            BillingCreditDocument(
                id=derive_save_credit_id(business.id),
                business_id=business.id,
                kind=BillingCreditKind.GRANTED,
                amount_minor=BillingCreditAmountMinor(
                    int(offer.credit.money.amount_minor)
                ),
                currency_code=offer.credit.money.currency_code,
                save_offer_for=subscription.id,
                created_at=now,
                updated_at=now,
            )
        )
        if not is_granted:
            raise ConflictError("The one-time credit was already given.")
