from app.contracts.repositories.referral_repositories import PartnerRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.dto.referrals.partner_admin import AdminPartnersQuery, PartnerList
from app.use_cases.referrals.partner_summaries import PartnerReaders
from app.use_cases.referrals.partners.partner_admin_gate import PartnerAdminGate
from app.use_cases.referrals.partners.partner_admin_views import (
    build_partner_admin_view,
)


class ListPartnersUseCase(UseCaseContract[AdminPartnersQuery, PartnerList]):
    """
    GET /v1/admin/partners (VIEW_CLIENTS): every partner, the newest first,
    with how they sign in, their rate and state, codes with links, the
    businesses they brought and paid, and their commissions per currency
    and status. Partners are a short list the platform team keeps.
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

    def run(self, input_data: AdminPartnersQuery) -> PartnerList:
        self._gate.admit(input_data.user_id, PlatformAdminPermission.VIEW_CLIENTS)
        partners = sorted(
            self._partner_repo.list_partners(),
            key=lambda partner: int(partner.created_at),
            reverse=True,
        )
        return PartnerList(
            items=[
                build_partner_admin_view(partner, self._readers) for partner in partners
            ]
        )
