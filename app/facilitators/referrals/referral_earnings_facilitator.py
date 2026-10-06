import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.referrals import ReferralEarningsFacilitatorContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.client_care_repositories import (
    BillingCreditRepoContract,
)
from app.contracts.repositories.referral_repositories import (
    CommissionEntryRepoContract,
    PartnerRepoContract,
    ReferralRepoContract,
)
from app.contracts.storage import StorageScopeContract
from app.schemas.constants.billing import BillingCreditKind, InvoiceStatus
from app.schemas.constants.referrals import PartnerStatus, ReferralCodeOwnerKind
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.referrals import (
    BusinessReferral,
    CommissionEntryDocument,
    ReferralDocument,
)
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import (
    BillingCreditAmountMinor,
    MoneyAmountMinor,
)
from app.schemas.typings.referrals.prefixed_id import PartnerId
from app.utilities.referrals.commission_math import commission_minor, commission_month
from app.utilities.referrals.referral_identity import (
    RewardSide,
    commission_entry_id,
    referral_id,
    reward_credit_id,
)
from app.utilities.referrals.reward_amounts import latest_subscription, month_of_service

logger: logging.Logger = logging.getLogger(__name__)


class ReferralEarningsFacilitator(ReferralEarningsFacilitatorContract):
    """
    What the paid invoices of a referred business earn (called by the
    payment webhook and by an admin's manual payment, platform-wide since
    the earnings land on other businesses and on partners):

    - a partner's business: on every paid invoice with money in it, the
      active partner's commission at their rate of now on what the invoice
      charged before tax, once per invoice (the entry's id derives from it);
    - an owner's invitation: on the first such invoice, a month of credit
      for the business and one for the business that invited it, each in
      the currency it pays, once (the lines' ids derive from the referral).

    Both are idempotent, so a repeated notification or two payments at once
    write each earning once. A failure is logged, never raised: the payment
    itself is already booked.
    """

    def __init__(
        self,
        referral_repo: ReferralRepoContract,
        partner_repo: PartnerRepoContract,
        commission_entry_repo: CommissionEntryRepoContract,
        billing_credit_repo: BillingCreditRepoContract,
        subscription_repo: SubscriptionRepoContract,
        business_repo: BusinessRepoContract,
        plan_registry: PlanRegistryContract,
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._referrals: ReferralRepoContract = referral_repo
        self._partners: PartnerRepoContract = partner_repo
        self._commissions: CommissionEntryRepoContract = commission_entry_repo
        self._credits: BillingCreditRepoContract = billing_credit_repo
        self._subscriptions: SubscriptionRepoContract = subscription_repo
        self._businesses: BusinessRepoContract = business_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._storage_scope: StorageScopeContract = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def record_paid_invoices(
        self, business: BusinessDocument, invoices: list[InvoiceDocument]
    ) -> None:
        referral: BusinessReferral | None = business.referred_by
        paid: list[InvoiceDocument] = [
            invoice
            for invoice in invoices
            if invoice.status is InvoiceStatus.PAID and int(invoice.amount_minor) > 0
        ]
        if referral is None or paid == []:
            return

        try:
            with self._storage_scope.platform_wide():
                now: Microseconds = self._wall_clock.now_unix()
                if referral.partner_id is not None:
                    self._accrue_commissions(business, referral.partner_id, paid, now)

                self._note_first_payment(business, referral, paid, now)
        except Exception:
            logger.exception(
                "Referral earnings of business %s (invoices %s) were not recorded.",
                business.id,
                ", ".join(str(invoice.id) for invoice in paid),
            )

    def _accrue_commissions(
        self,
        business: BusinessDocument,
        partner_id: PartnerId,
        paid: list[InvoiceDocument],
        now: Microseconds,
    ) -> None:
        partner: PartnerDocument | None = self._partners.get(partner_id)
        if partner is None or partner.status is not PartnerStatus.ACTIVE:
            return

        for invoice in paid:
            base: int = int(invoice.amount_minor) - int(invoice.tax_minor or 0)
            amount: int = commission_minor(
                base, int(partner.commission_rate_basis_points)
            )
            if base <= 0 or amount <= 0:
                continue

            accrued_at: Microseconds = invoice.paid_at or now
            self._commissions.record(
                CommissionEntryDocument(
                    id=commission_entry_id(invoice.id),
                    partner_id=partner.id,
                    business_id=business.id,
                    invoice_id=invoice.id,
                    base_minor=MoneyAmountMinor(base),
                    rate_basis_points=partner.commission_rate_basis_points,
                    amount_minor=MoneyAmountMinor(amount),
                    currency_code=invoice.currency_code,
                    accrued_at=accrued_at,
                    month=commission_month(accrued_at),
                    created_at=now,
                    updated_at=now,
                )
            )

    def _note_first_payment(
        self,
        business: BusinessDocument,
        referral: BusinessReferral,
        paid: list[InvoiceDocument],
        now: Microseconds,
    ) -> None:
        stored: ReferralDocument = self._referrals.get(
            referral_id(business.id)
        ) or ReferralDocument(
            id=referral_id(business.id),
            business_id=referral.referring_business_id,
            referred_business_id=business.id,
            code=referral.code,
            owner_kind=referral.owner_kind,
            partner_id=referral.partner_id,
            referred_at=referral.referred_at,
            created_at=now,
            updated_at=now,
        )
        is_changed: bool = False
        if stored.first_paid_at is None:
            stored.first_paid_at = min(
                (invoice.paid_at or now for invoice in paid), key=int
            )
            is_changed = True

        if (
            referral.owner_kind is ReferralCodeOwnerKind.BUSINESS
            and stored.rewarded_at is None
        ):
            self._grant_month(business, business, RewardSide.REFERRED, now)
            referring: BusinessDocument | None = (
                None
                if referral.referring_business_id is None
                else self._businesses.get(referral.referring_business_id)
            )
            if referring is not None:
                self._grant_month(referring, business, RewardSide.REFERRER, now)

            stored.rewarded_at = now
            is_changed = True

        if is_changed:
            stored.updated_at = now
            self._referrals.save(stored)

    def _grant_month(
        self,
        receiver: BusinessDocument,
        referred: BusinessDocument,
        side: RewardSide,
        now: Microseconds,
    ) -> None:
        month: Money = month_of_service(
            self._plan_registry,
            receiver,
            latest_subscription(self._subscriptions.list_by_business(receiver.id)),
        )
        if int(month.amount_minor) <= 0:
            return

        self._credits.record(
            BillingCreditDocument(
                id=reward_credit_id(referred.id, side),
                business_id=receiver.id,
                kind=BillingCreditKind.GRANTED,
                amount_minor=BillingCreditAmountMinor(int(month.amount_minor)),
                currency_code=month.currency_code,
                referral_of=referred.id,
                created_at=now,
                updated_at=now,
            )
        )
