from typed_time_provider import Microseconds

from app.contracts.repositories.referral_repositories import PartnerRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.referrals.partner_admin import (
    PartnerAdminView,
    UpdatePartnerCommand,
    UpdatePartnerRequest,
)
from app.use_cases.referrals.partner_summaries import PartnerReaders
from app.use_cases.referrals.partners.partner_admin_gate import (
    PARTNER_ENTITY,
    PartnerAdminGate,
)
from app.use_cases.referrals.partners.partner_admin_views import (
    build_partner_admin_view,
)


class UpdatePartnerUseCase(UseCaseContract[UpdatePartnerCommand, PartnerAdminView]):
    """
    PATCH /v1/admin/partners/{partner_id} (MANAGE_CLIENT_BILLING): rename a
    partner, change their rate (invoices paid from now on earn the new
    one; earned commissions keep theirs) or pause and resume them (a
    paused partner keeps what was earned and earns nothing new). Audited
    (UPDATE partner).
    """

    def __init__(
        self,
        gate: PartnerAdminGate,
        partner_repo: PartnerRepoContract,
        readers: PartnerReaders,
    ) -> None:
        self._gate: PartnerAdminGate = gate
        self._partner_repo: PartnerRepoContract = partner_repo
        self._readers: PartnerReaders = readers

    def run(self, input_data: UpdatePartnerCommand) -> PartnerAdminView:
        admin: UserDocument = self._gate.admit(
            input_data.user_id, PlatformAdminPermission.MANAGE_CLIENT_BILLING
        )
        partner: PartnerDocument = self._gate.require_partner(input_data.partner_id)
        request: UpdatePartnerRequest = input_data.request
        now: Microseconds = self._gate.now()
        if request.name is not None:
            partner.name = request.name
        if request.commission_rate_basis_points is not None:
            partner.commission_rate_basis_points = request.commission_rate_basis_points
        if request.status is not None:
            partner.status = request.status

        partner.updated_at = now
        self._partner_repo.save(partner)
        self._gate.record(
            admin,
            AuditAction.UPDATE,
            PARTNER_ENTITY,
            partner.id,
            input_data.client_ip_address,
        )
        return build_partner_admin_view(partner, self._readers)
