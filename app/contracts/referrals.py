"""
The referral program's side effects other contexts call (migration 1150):
links that carry a business's code, who brought a new business, and the
earnings of a paid invoice (a partner's commission, the first-payment
rewards of an owner's invitation).
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.referrals import BusinessReferral
from app.schemas.domain.users import UserDocument
from app.schemas.typings.analytics.constrained_strings import (
    ReferralCode,
    SignupSourceTag,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.referrals.constrained_strings import ReferralLink


class ReferralLinksFacilitatorContract(FacilitatorContract, Protocol):
    def business_code(self, business_id: BusinessId) -> ReferralCode | None:
        """
        The business's own code, claimed on first use (None only when every
        candidate is taken, which never happens in practice).
        """
        raise NotImplementedError

    def link_for(
        self, business_id: BusinessId, source: SignupSourceTag
    ) -> ReferralLink | None:
        """
        The platform's site with the business's code and `source` (None
        without CABINET_BASE_URL or a code).
        """
        raise NotImplementedError

    def powered_by_link(
        self, business: BusinessDocument, source: SignupSourceTag
    ) -> ReferralLink | None:
        """
        The "Powered by" link of the business's chat, hosted page or table
        card; None when a Plus owner switched it off or there is no link.
        """
        raise NotImplementedError


class ReferralAttributionFacilitatorContract(FacilitatorContract, Protocol):
    def referral_of(
        self, owner: UserDocument, business_id: BusinessId, now: Microseconds
    ) -> BusinessReferral | None:
        """
        Who brought a new business: the code its owner signed up by, when it
        names an active partner or another business the owner does not
        work in; None otherwise (no code, an unknown code, a self-referral).
        """
        raise NotImplementedError

    def record(self, business: BusinessDocument) -> None:
        """
        Remember a business that `referral_of` attributed (stored), once:
        the partner's portal and the inviting owner's counts read it.
        """
        raise NotImplementedError


class ReferralEarningsFacilitatorContract(FacilitatorContract, Protocol):
    def record_paid_invoices(
        self, business: BusinessDocument, invoices: list[InvoiceDocument]
    ) -> None:
        """
        What the paid invoices of a referred business earn: the partner's
        commission on each (once per invoice, never on a zero amount) and,
        on the business's first paid invoice, a month of credit for it and
        for the business that invited it (once). Never raises: a failure is
        logged with the invoices, so a payment is never refused for it.
        """
        raise NotImplementedError
