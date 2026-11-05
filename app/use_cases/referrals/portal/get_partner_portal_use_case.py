from app.contracts.repositories.referral_repositories import PartnerRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.partners import PartnerDocument
from app.schemas.dto.referrals.partner_portal import (
    PartnerPortalQuery,
    PartnerPortalView,
)
from app.use_cases.referrals.partner_summaries import (
    PartnerReaders,
    PartnerSummary,
    require_partner,
)


class GetPartnerPortalUseCase(UseCaseContract[PartnerPortalQuery, PartnerPortalView]):
    """
    GET /v1/partner: the signed-in partner's portal (the person signs in
    with the phone number or e-mail the platform team recorded): their
    rate and state, their codes with links, how many businesses signed up
    by them and paid, and their commissions per currency, to be paid and
    paid. Anyone else gets 404.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        partner_repo: PartnerRepoContract,
        readers: PartnerReaders,
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._partner_repo: PartnerRepoContract = partner_repo
        self._readers: PartnerReaders = readers

    def run(self, input_data: PartnerPortalQuery) -> PartnerPortalView:
        partner: PartnerDocument = require_partner(
            self._user_repo, self._partner_repo, input_data.user_id
        )
        summary: PartnerSummary = self._readers.summarize(partner)
        return PartnerPortalView(
            partner_id=partner.id,
            name=partner.name,
            status=partner.status,
            commission_rate_basis_points=partner.commission_rate_basis_points,
            codes=summary.codes,
            referred_businesses=summary.referred_businesses,
            paid_businesses=summary.paid_businesses,
            totals=summary.totals,
        )
