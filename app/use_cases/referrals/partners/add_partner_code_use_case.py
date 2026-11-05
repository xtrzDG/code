from app.contracts.repositories.referral_repositories import ReferralCodeRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.referrals.partner_admin import (
    AddPartnerCodeCommand,
    PartnerAdminView,
)
from app.use_cases.referrals.partner_summaries import PartnerReaders
from app.use_cases.referrals.partners.partner_admin_gate import (
    PARTNER_CODE_ENTITY,
    PartnerAdminGate,
)
from app.use_cases.referrals.partners.partner_admin_views import (
    build_partner_admin_view,
)
from app.use_cases.referrals.partners.partner_codes import claim_partner_code


class AddPartnerCodeUseCase(UseCaseContract[AddPartnerCodeCommand, PartnerAdminView]):
    """
    POST /v1/admin/partners/{partner_id}/codes (MANAGE_CLIENT_BILLING):
    another code for a partner (a campaign of theirs, a second agency
    brand). A code in use in any case answers 409 `code_taken`. Audited
    (UPDATE partner_code).
    """

    def __init__(
        self,
        gate: PartnerAdminGate,
        referral_code_repo: ReferralCodeRepoContract,
        readers: PartnerReaders,
    ) -> None:
        self._gate: PartnerAdminGate = gate
        self._codes: ReferralCodeRepoContract = referral_code_repo
        self._readers: PartnerReaders = readers

    def run(self, input_data: AddPartnerCodeCommand) -> PartnerAdminView:
        admin: UserDocument = self._gate.admit(
            input_data.user_id, PlatformAdminPermission.MANAGE_CLIENT_BILLING
        )
        partner: PartnerDocument = self._gate.require_partner(input_data.partner_id)
        claim_partner_code(
            self._codes, partner.id, input_data.request.code, self._gate.now()
        )
        self._gate.record(
            admin,
            AuditAction.UPDATE,
            PARTNER_CODE_ENTITY,
            partner.id,
            input_data.client_ip_address,
        )
        return build_partner_admin_view(partner, self._readers)
