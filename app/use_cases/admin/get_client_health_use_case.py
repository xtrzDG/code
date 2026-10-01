from app.contracts.billing import PaymentOrderRepoContract
from app.contracts.repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
    BusinessRepoContract,
    InvoiceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AutotestOutcome
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
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
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.users.prefixed_id import UserId

MAX_LISTED_INVOICES: int = 24
MAX_LISTED_PAYMENTS: int = 20


class GetClientHealthUseCase(UseCaseContract[AdminClientQuery, ClientHealthView]):
    """
    One client in detail for the platform admin: the summary, the scenarios
    that failed in the latest autotest run, recent invoices and payment
    attempts with the provider's decline reasons. No visitor personal data
    is shown, so the view is not audited; entering the cabinet is.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[UserId, UserDocument],
        business_repo: BusinessRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        invoice_repo: InvoiceRepoContract,
        payment_order_repo: PaymentOrderRepoContract,
        summarize_client: UseCaseContract[ClientSummarySource, AdminClientSummary],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[UserId, UserDocument] = (
            authorize_platform_admin
        )
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
        self._authorize_platform_admin.run(input_data.user_id)
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        return ClientHealthView(
            summary=self._summarize_client.run(ClientSummarySource(business=business)),
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
                )
                for invoice in self._invoice_repo.list_by_business(business.id)[
                    :MAX_LISTED_INVOICES
                ]
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
        runs: list[AutotestRunDocument] = []
        versions: list[AssistantVersionDocument] = sorted(
            self._assistant_version_repo.list_by_business(business.id),
            key=lambda version: version.version_number,
            reverse=True,
        )
        for version in versions:
            if version.autotest_run_id is None:
                continue

            run: AutotestRunDocument | None = self._autotest_run_repo.get(
                business.id,
                version.autotest_run_id,
            )
            if run is not None:
                runs.append(run)
                break

        return [
            FailedAutotestView(
                scenario_key=result.scenario_key,
                kind=result.kind,
                language=result.language,
                outcome=result.outcome,
                judge_notes=list(result.judge_notes),
            )
            for run in runs
            for result in run.results
            if result.outcome is not AutotestOutcome.PASSED
        ]
