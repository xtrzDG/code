"""A referred business in its trial: invited by another owner or a partner's."""

from dataclasses import dataclass

from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.constants.referrals import PartnerStatus, ReferralCodeOwnerKind
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.domain.referrals import (
    BusinessReferral,
    CommissionEntryDocument,
    ReferralDocument,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.analytics.constrained_strings import ReferralCode
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.referrals.constrained_integers import (
    CommissionRateBasisPoints,
)
from app.schemas.typings.referrals.constrained_strings import PartnerName
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.referrals.referral_identity import partner_id_for, referral_id
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.paid_world import PaidWorld, build_trial

INVITE_CODE: ReferralCode = ReferralCode("invite-code-01")
PARTNER_CODE: ReferralCode = ReferralCode("agency-tbilisi")
PARTNER_RATE: CommissionRateBasisPoints = CommissionRateBasisPoints(2000)


@dataclass(frozen=True)
class ReferredWorld:
    paid: PaidWorld
    referring: BusinessDocument | None
    partner: PartnerDocument | None

    @property
    def business_id(self) -> BusinessId:
        return self.paid.business.id

    def credits(self, business_id: BusinessId) -> list[BillingCreditDocument]:
        return self.paid.testbed.billing_credit_repo.list_by_business(business_id)

    def referral(self) -> ReferralDocument:
        stored: ReferralDocument | None = self.paid.testbed.referrals.referral_repo.get(
            referral_id(self.business_id)
        )
        assert stored is not None
        return stored

    def commissions(self) -> list[CommissionEntryDocument]:
        assert self.partner is not None
        return self.paid.testbed.referrals.commission_entry_repo.page_by_partner(
            self.partner.id, KeysetSlice(limit=KeysetReadLimit(50))
        )

    def renew(self, order: PaymentOrderDocument, payment_id: int) -> None:
        testbed = self.paid.testbed
        period_end = testbed.subscription(self.business_id).period_end
        testbed.clock.move_to(period_end)
        testbed.clock.advance(hours=2)
        receipt = testbed.deliver_flitt_callback(
            {
                **testbed.callback_parameters(
                    order, "approved", payment_id=payment_id, amount=51700
                ),
                "order_id": f"{order.id}_{payment_id}",
                "parent_order_id": str(order.id),
            }
        )
        assert receipt.outcome is PaymentWebhookOutcome.APPLIED


def invited_trial() -> ReferredWorld:
    """A trial business its owner signed up for by another owner's invitation."""

    paid = build_trial()
    inviter = paid.testbed.add_user(email="inviter@example.com")
    referring = paid.testbed.add_business(inviter, name="Old Town Bakery")
    refer_by_invitation(paid.testbed, paid.business.id, referring)
    return ReferredWorld(paid=paid, referring=referring, partner=None)


def partner_trial(status: PartnerStatus = PartnerStatus.ACTIVE) -> ReferredWorld:
    """A trial business its owner signed up for by a partner's link."""

    paid = build_trial()
    partner = add_partner(paid.testbed, status)
    refer_by_partner(paid.testbed, paid.business.id, partner)
    return ReferredWorld(paid=paid, referring=None, partner=partner)


def add_partner(
    testbed: BillingTestbed, status: PartnerStatus = PartnerStatus.ACTIVE
) -> PartnerDocument:
    partner = PartnerDocument(
        id=partner_id_for("phone:+995599000111"),
        name=PartnerName("Tbilisi Digital"),
        login_method=LoginMethod.PHONE,
        phone_number=E164PhoneNumber("+995599000111"),
        commission_rate_basis_points=PARTNER_RATE,
        status=status,
        added_by=UserId(),
    )
    testbed.referrals.partner_repo.add(partner)
    return partner


def refer_by_partner(
    testbed: BillingTestbed, business_id: BusinessId, partner: PartnerDocument
) -> None:
    _refer(
        testbed,
        business_id,
        BusinessReferral(
            code=PARTNER_CODE,
            owner_kind=ReferralCodeOwnerKind.PARTNER,
            partner_id=partner.id,
            referred_at=testbed.clock.now(),
        ),
    )


def refer_by_invitation(
    testbed: BillingTestbed, business_id: BusinessId, referring: BusinessDocument
) -> None:
    _refer(
        testbed,
        business_id,
        BusinessReferral(
            code=INVITE_CODE,
            owner_kind=ReferralCodeOwnerKind.BUSINESS,
            referring_business_id=referring.id,
            referred_at=testbed.clock.now(),
        ),
    )


def _refer(
    testbed: BillingTestbed, business_id: BusinessId, referral: BusinessReferral
) -> None:
    business = testbed.business(business_id)
    business.referred_by = referral
    testbed.business_repo.save(business)
    testbed.referrals.referral_repo.record(
        ReferralDocument(
            id=referral_id(business.id),
            business_id=referral.referring_business_id,
            referred_business_id=business.id,
            code=referral.code,
            owner_kind=referral.owner_kind,
            partner_id=referral.partner_id,
            referred_at=referral.referred_at,
        )
    )
