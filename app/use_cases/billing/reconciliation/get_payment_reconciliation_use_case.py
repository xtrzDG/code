from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_safety import PaymentReconciliationRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payment_reconciliations import (
    PaymentMismatch,
    PaymentReconciliationDocument,
)
from app.schemas.domain.users import UserDocument
from app.schemas.dto.payment_reconciliation import (
    PaymentMismatchView,
    PaymentReconciliationQuery,
    PaymentReconciliationView,
)
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.use_cases.shared.payment_reconciliation_days import (
    latest_reconciliation,
)


class GetPaymentReconciliationUseCase(
    UseCaseContract[PaymentReconciliationQuery, PaymentReconciliationView]
):
    """
    The latest daily payment reconciliation for the platform admin (today's,
    else yesterday's): when it ran, how many orders it compared with Flitt
    and Stripe, how many they could not tell about, and each mismatch with
    its client's name. Payments are money: SUPER and BILLING admins
    (MANAGE_CLIENT_BILLING) only.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        reconciliation_repo: PaymentReconciliationRepoContract,
        business_repo: BusinessRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._reconciliation_repo: PaymentReconciliationRepoContract = (
            reconciliation_repo
        )
        self._business_repo: BusinessRepoContract = business_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PaymentReconciliationQuery) -> PaymentReconciliationView:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_CLIENT_BILLING,
            )
        )
        latest: PaymentReconciliationDocument | None = latest_reconciliation(
            self._reconciliation_repo, self._wall_clock.now_unix()
        )
        if latest is None:
            return PaymentReconciliationView()

        return PaymentReconciliationView(
            day=latest.day,
            ran_at=latest.ran_at,
            checked_count=latest.checked_count,
            unreadable_count=latest.unreadable_count,
            mismatches=[self._view(mismatch) for mismatch in latest.mismatches],
        )

    def _view(self, mismatch: PaymentMismatch) -> PaymentMismatchView:
        business: BusinessDocument | None = self._business_repo.get(
            mismatch.business_id
        )
        return PaymentMismatchView(
            payment_order_id=mismatch.payment_order_id,
            business_id=mismatch.business_id,
            business_name=None if business is None else business.name,
            provider=mismatch.provider,
            recorded_status=mismatch.recorded_status,
            provider_status=mismatch.provider_status,
            kind=mismatch.kind,
        )
