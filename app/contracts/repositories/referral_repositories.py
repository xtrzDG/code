"""
Persistence contracts of the referral and partner program (migration
1150): partners, referral codes, the businesses referred and the
partners' commissions.
"""

from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.referrals import CommissionStatus
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.referrals import (
    CommissionEntryDocument,
    ReferralCodeDocument,
    ReferralDocument,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.referrals.commission_totals import CommissionTotal
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.referrals.constrained_integers import ReferredBusinessCount
from app.schemas.typings.referrals.constrained_strings import CommissionMonth
from app.schemas.typings.referrals.prefixed_id import (
    PartnerId,
    ReferralCodeId,
    ReferralId,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.users.constrained_strings import EmailAddress


class PartnerRepoContract(RepoContract, Protocol):
    """The partners (a platform collection; dozens of rows, not millions)."""

    def add(self, partner: PartnerDocument) -> bool:
        """Store a new partner unless one with its id exists. True if stored."""
        raise NotImplementedError

    def save(self, partner: PartnerDocument) -> None:
        raise NotImplementedError

    def get(self, partner_id: PartnerId) -> PartnerDocument | None:
        raise NotImplementedError

    def get_many(self, partner_ids: list[PartnerId]) -> list[PartnerDocument]:
        raise NotImplementedError

    def find_by_phone_number(
        self, phone_number: E164PhoneNumber
    ) -> PartnerDocument | None:
        raise NotImplementedError

    def find_by_email(self, email: EmailAddress) -> PartnerDocument | None:
        raise NotImplementedError

    def list_partners(self) -> list[PartnerDocument]:
        """Every partner, active ones first (one indexed read per status)."""
        raise NotImplementedError


class ReferralCodeRepoContract(RepoContract, Protocol):
    def claim(self, code: ReferralCodeDocument) -> bool:
        """
        Store the code unless it is taken (atomic, also across processes).
        True when stored; False when the code already names someone.
        """
        raise NotImplementedError

    def get(self, code_id: ReferralCodeId) -> ReferralCodeDocument | None:
        raise NotImplementedError

    def list_by_partner(self, partner_id: PartnerId) -> list[ReferralCodeDocument]:
        raise NotImplementedError


class ReferralRepoContract(RepoContract, Protocol):
    def record(self, referral: ReferralDocument) -> bool:
        """Store the referral unless the business was referred already."""
        raise NotImplementedError

    def get(self, referral_id: ReferralId) -> ReferralDocument | None:
        raise NotImplementedError

    def save(self, referral: ReferralDocument) -> None:
        raise NotImplementedError

    def page_by_partner(
        self, partner_id: PartnerId, window: KeysetSlice
    ) -> list[ReferralDocument]:
        """A partner's referred businesses, newest first (one keyset page)."""
        raise NotImplementedError

    def count_by_partner(
        self, partner_id: PartnerId, *, only_paid: bool = False
    ) -> ReferredBusinessCount:
        """How many businesses the partner brought (or of them have paid)."""
        raise NotImplementedError

    def list_invited_by(
        self, business_id: BusinessId, limit: DocumentQueryLimit
    ) -> list[ReferralDocument]:
        """The businesses an owner invited, oldest first, at most `limit`."""
        raise NotImplementedError


class CommissionEntryRepoContract(RepoContract, Protocol):
    def record(self, entry: CommissionEntryDocument) -> bool:
        """Store the commission unless its invoice earned one already."""
        raise NotImplementedError

    def save(self, entry: CommissionEntryDocument) -> None:
        raise NotImplementedError

    def page_by_partner(
        self, partner_id: PartnerId, window: KeysetSlice
    ) -> list[CommissionEntryDocument]:
        """A partner's commissions, newest first (one keyset page)."""
        raise NotImplementedError

    def totals_by_partner(self, partner_id: PartnerId) -> list[CommissionTotal]:
        """A partner's commissions summed per currency and status (database)."""
        raise NotImplementedError

    def totals_of_month(self, month: CommissionMonth) -> list[CommissionTotal]:
        """A payout month summed per partner, currency and status (database)."""
        raise NotImplementedError

    def list_of_month(
        self,
        partner_id: PartnerId,
        month: CommissionMonth,
        status: CommissionStatus,
    ) -> list[CommissionEntryDocument]:
        """A partner's commissions of one month in one status."""
        raise NotImplementedError
