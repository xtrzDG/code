from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.referral_repositories import (
    CommissionEntryRepoContract,
    PartnerRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.referrals import CommissionEntryDocument
from app.schemas.dto.referrals.partner_portal import (
    CommissionEntryPage,
    CommissionEntryView,
    PartnerPageQuery,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.referrals.partner_summaries import require_partner
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListPartnerCommissionsUseCase(
    UseCaseContract[PartnerPageQuery, CommissionEntryPage]
):
    """
    GET /v1/partner/commissions?limit=&cursor=: the partner's commissions,
    the newest first: the business, the month, what the invoice charged
    before tax, the rate, the share and whether it was paid out.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        partner_repo: PartnerRepoContract,
        commission_entry_repo: CommissionEntryRepoContract,
        business_repo: BusinessRepoContract,
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._partner_repo: PartnerRepoContract = partner_repo
        self._commissions: CommissionEntryRepoContract = commission_entry_repo
        self._businesses: BusinessRepoContract = business_repo

    def run(self, input_data: PartnerPageQuery) -> CommissionEntryPage:
        partner: PartnerDocument = require_partner(
            self._user_repo, self._partner_repo, input_data.user_id
        )
        entries, next_cursor = finish_page(
            self._commissions.page_by_partner(partner.id, read_slice(input_data.page)),
            input_data.page,
            sort_key=lambda entry: int(entry.accrued_at),
            item_id=lambda entry: str(entry.id),
        )
        businesses: dict[BusinessId, BusinessDocument] = {
            business.id: business
            for business in self._businesses.get_many(
                list(dict.fromkeys(entry.business_id for entry in entries))
            )
        }
        return CommissionEntryPage(
            items=[
                entry_view(entry, businesses.get(entry.business_id))
                for entry in entries
            ],
            next_cursor=next_cursor,
        )


def entry_view(
    entry: CommissionEntryDocument, business: BusinessDocument | None
) -> CommissionEntryView:
    return CommissionEntryView(
        id=entry.id,
        business_id=entry.business_id,
        business_name=None if business is None else business.name,
        month=entry.month,
        base_minor=entry.base_minor,
        rate_basis_points=entry.rate_basis_points,
        amount_minor=entry.amount_minor,
        currency_code=entry.currency_code,
        status=entry.status,
        accrued_at=entry.accrued_at,
        paid_at=entry.paid_at,
    )
