from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    ChangePlanCommand,
    ChangePlanRequest,
    CheckoutSessionView,
    StartCheckoutCommand,
    StartCheckoutRequest,
    SubscribeCommand,
    SubscriptionOpening,
)


class SubscribeOrchestrator(
    OrchestratorContract[SubscribeCommand, CheckoutSessionView]
):
    """
    Owner subscribes to a plan and pays now (POST .../billing/subscribe):
    after the trial, after cancelling, or without a trial at all.

    1. Open the subscription: a business without one gets an unpaid
       (INCOMPLETE) subscription for the chosen plan and period.
    2. An existing subscription switches to the chosen plan and period with
       the plan-change rules (old automatic charges stopped, bills at the
       old price voided); the same plan changes nothing.
    3. Checkout with the usual rules: open bills first, a fresh period from
       now when the unpaid one has ended, the setup fee with the first
       monthly period, a paid bill never collected again, and automatic
       charges of the subscription price from the end of the paid period.
    """

    def __init__(
        self,
        open_subscription: UseCaseContract[SubscribeCommand, SubscriptionOpening],
        change_plan: UseCaseContract[ChangePlanCommand, BillingOverview],
        start_checkout: UseCaseContract[StartCheckoutCommand, CheckoutSessionView],
    ) -> None:
        self._open_subscription: UseCaseContract[
            SubscribeCommand,
            SubscriptionOpening,
        ] = open_subscription
        self._change_plan: UseCaseContract[ChangePlanCommand, BillingOverview] = (
            change_plan
        )
        self._start_checkout: UseCaseContract[
            StartCheckoutCommand,
            CheckoutSessionView,
        ] = start_checkout

    def execute(self, input_data: SubscribeCommand) -> CheckoutSessionView:
        opening: SubscriptionOpening = self._open_subscription.run(input_data)
        if not opening.is_created:
            self._change_plan.run(
                ChangePlanCommand(
                    user_id=input_data.user_id,
                    business_id=input_data.business_id,
                    request=ChangePlanRequest(
                        plan_key=input_data.request.plan_key,
                        billing_period=input_data.request.billing_period,
                    ),
                    display_language=input_data.display_language,
                )
            )

        return self._start_checkout.run(
            StartCheckoutCommand(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                request=StartCheckoutRequest(return_url=input_data.request.return_url),
                display_language=input_data.display_language,
            )
        )
