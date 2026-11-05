from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import PaymentOrderRepoContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.client_care_repositories import (
    BillingCreditRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.assistants import AutotestOutcome
from app.schemas.domain.assistants import AutotestRunDocument
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin import (
    AdminClientQuery,
    AdminClientSummary,
    AdminInvoiceView,
    AdminPaymentView,
    ClientHealthView,
    ClientSummarySource,
    FailedAutotestView,
)
from app.schemas.dto.billing import Money
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.assistants.prefixed_id import AutotestRunId
from app.use_cases.admin.active_version import find_active_version, find_verdict_run_id
from app.use_cases.admin.client_account_view import build_client_account
from app.use_cases.shared.billing_records import find_current_subscription
from app.utilities.assembly.autotest_evaluation import MIN_PASSING_CRITERION_SCORE

MAX_LISTED_INVOICES: int = 24
MAX_LISTED_PAYMENTS: int = 20


class GetClientHealthUseCase(UseCaseContract[AdminClientQuery, ClientHealthView]):
    """
    One client in detail for the platform admin: the summary, the scenarios
    that failed in the run behind the active version's verdict (with why, as
    codes), recent invoices and payment
    attempts with the provider's decline reasons. No visitor personal data
    is shown, so the view is not audited; entering the cabinet is.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        invoice_repo: InvoiceRepoContract,
        payment_order_repo: PaymentOrderRepoContract,
        summarize_client: UseCaseContract[ClientSummarySource, AdminClientSummary],
        subscription_repo: SubscriptionRepoContract,
        billing_credit_repo: BillingCreditRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._billing_credit_repo: BillingCreditRepoContract = billing_credit_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._business_repo: BusinessRepoContract = business_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo
        self._summarize_client: UseCaseContract[
            ClientSummarySource,
            AdminClientSummary,
        ] = summarize_client

    def run(self, input_data: AdminClientQuery) -> ClientHealthView:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_CLIENTS,
            )
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        invoices: list[InvoiceDocument] = self._invoice_repo.list_by_business(
            business.id
        )
        return ClientHealthView(
            summary=self._summarize_client.run(ClientSummarySource(business=business)),
            account=build_client_account(
                find_current_subscription(self._subscription_repo, business.id),
                self._billing_credit_repo.list_by_business(business.id),
                invoices,
                self._wall_clock.now_unix(),
            ),
            timezone=business.timezone,
            failed_autotests=self._list_failed_autotests(business),
            invoices=[
                AdminInvoiceView(
                    id=invoice.id,
                    kind=invoice.kind,
                    amount=Money(
                        amount_minor=invoice.amount_minor,
                        currency_code=invoice.currency_code,
                    ),
                    status=invoice.status,
                    period_start=invoice.period_start,
                    period_end=invoice.period_end,
                    number=invoice.number,
                    manual_payment_method=(
                        None
                        if invoice.manual_payment is None
                        else invoice.manual_payment.method
                    ),
                )
                for invoice in invoices[:MAX_LISTED_INVOICES]
            ],
            payments=[
                AdminPaymentView(
                    id=payment_order.id,
                    status=payment_order.status,
                    amount=Money(
                        amount_minor=payment_order.amount_minor,
                        currency_code=payment_order.currency_code,
                    ),
                    created_at=payment_order.created_at,
                    failure_reason=payment_order.last_failure_reason,
                    is_refund_due=payment_order.is_refund_due,
                )
                for payment_order in self._payment_order_repo.list_by_business(
                    business.id
                )[:MAX_LISTED_PAYMENTS]
            ],
        )

    def _list_failed_autotests(
        self,
        business: BusinessDocument,
    ) -> list[FailedAutotestView]:
        run_id: AutotestRunId | None = find_verdict_run_id(
            find_active_version(self._assistant_version_repo, business)
        )
        run: AutotestRunDocument | None = (
            None if run_id is None else self._autotest_run_repo.get(business.id, run_id)
        )
        if run is None:
            return []

        return [
            FailedAutotestView(
                scenario_key=result.scenario_key,
                kind=result.kind,
                language=result.language,
                outcome=result.outcome,
                judge_notes=list(result.judge_notes),
                check_codes=list(result.check_codes),
                low_criteria=[
                    score.criterion
                    for score in result.scores
                    if int(score.score) < MIN_PASSING_CRITERION_SCORE
                ],
            )
            for result in run.results
            if result.outcome is not AutotestOutcome.PASSED
        ]
