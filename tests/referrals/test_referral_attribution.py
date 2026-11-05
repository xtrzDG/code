"""Who brought a new business, from the code its owner signed up by."""

from app.schemas.constants.referrals import (
    PartnerStatus,
    ReferralCodeOwnerKind,
)
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.referrals import BusinessReferral, ReferralCodeDocument
from app.schemas.domain.signup_attribution import SignupAttribution
from app.schemas.domain.users import UserDocument
from app.schemas.typings.analytics.constrained_strings import ReferralCode
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.referrals.referral_identity import referral_code_id, referral_id
from tests.billing.billing_testbed import BillingTestbed
from tests.referrals.referral_billing_world import PARTNER_CODE, add_partner


class AttributionWorld:
    def __init__(self) -> None:
        self.testbed = testbed = BillingTestbed()
        self.attribution = testbed.referrals.attribution(
            testbed.business_repo, testbed.clock.wall_clock
        )
        self.links = testbed.referrals.links(testbed.clock.wall_clock)
        inviter = testbed.add_user(email="inviter@example.com")
        self.inviting = testbed.add_business(inviter, name="Old Town Bakery")
        code = self.links.business_code(self.inviting.id)
        assert code is not None
        self.invite_code: ReferralCode = code

    def owner(self, code: str | None, phone: str = "+995599777888") -> UserDocument:
        user = self.testbed.add_user(phone_number=phone)
        user.created_at = self.testbed.clock.now()
        user.signup_attribution = (
            None
            if code is None
            else SignupAttribution(referral_code=ReferralCode(code))
        )
        self.testbed.user_repo.save(user)
        return user

    def partner_code(self, status: PartnerStatus = PartnerStatus.ACTIVE) -> None:
        partner = add_partner(self.testbed, status)
        self.testbed.referrals.referral_code_repo.claim(
            ReferralCodeDocument(
                id=referral_code_id(PARTNER_CODE),
                code=PARTNER_CODE,
                owner_kind=ReferralCodeOwnerKind.PARTNER,
                partner_id=partner.id,
            )
        )

    def refer(
        self, owner: UserDocument, business_id: BusinessId | None = None
    ) -> BusinessReferral | None:
        return self.attribution.referral_of(
            owner, business_id or BusinessId(), self.testbed.clock.now()
        )


def test_an_invited_owner_is_referred_by_the_inviting_business() -> None:
    world = AttributionWorld()

    referral = world.refer(world.owner(str(world.invite_code)))

    assert referral is not None
    assert referral.owner_kind is ReferralCodeOwnerKind.BUSINESS
    assert referral.referring_business_id == world.inviting.id
    assert referral.partner_id is None
    assert referral.code == world.invite_code


def test_a_partners_code_refers_to_the_partner_even_while_paused() -> None:
    world = AttributionWorld()
    world.partner_code(PartnerStatus.PAUSED)

    referral = world.refer(world.owner(str(PARTNER_CODE)))

    assert referral is not None
    assert referral.owner_kind is ReferralCodeOwnerKind.PARTNER
    assert referral.partner_id is not None
    assert referral.referring_business_id is None


def test_a_partner_opening_their_own_business_refers_nobody() -> None:
    world = AttributionWorld()
    world.partner_code()

    partner_person = world.owner(str(PARTNER_CODE), phone="+995599000111")

    assert world.refer(partner_person) is None


def test_a_member_of_the_inviting_business_refers_nobody() -> None:
    world = AttributionWorld()
    member = world.owner(str(world.invite_code))
    inviting = world.testbed.business(world.inviting.id)
    inviting.members.append(
        BusinessMember(user_id=member.id, role=BusinessMemberRole.STAFF)
    )
    world.testbed.business_repo.save(inviting)

    assert world.refer(member) is None


def test_a_business_never_refers_itself() -> None:
    world = AttributionWorld()

    owner = world.owner(str(world.invite_code))

    assert world.refer(owner, business_id=world.inviting.id) is None


def test_no_code_or_an_unknown_code_refers_nobody() -> None:
    world = AttributionWorld()

    assert world.refer(world.owner(None)) is None
    assert world.refer(world.owner("nobody-1", phone="+995599777889")) is None


def test_a_code_counts_for_ninety_days_after_sign_up() -> None:
    world = AttributionWorld()
    owner = world.owner(str(world.invite_code))

    world.testbed.clock.advance(days=89)
    assert world.refer(owner) is not None

    world.testbed.clock.advance(days=2)
    assert world.refer(owner) is None


def test_recording_a_referral_lists_it_for_the_inviting_business() -> None:
    world = AttributionWorld()
    owner = world.owner(str(world.invite_code))
    business: BusinessDocument = world.testbed.add_business(owner, name="Bia 2")
    business.referred_by = world.refer(owner, business.id)
    world.testbed.business_repo.save(business)

    world.attribution.record(business)
    world.attribution.record(world.testbed.business(world.inviting.id))

    stored = world.testbed.referrals.referral_repo.get(referral_id(business.id))
    assert stored is not None
    assert stored.business_id == world.inviting.id
    assert stored.referred_business_id == business.id
    assert (
        world.testbed.referrals.referral_repo.get(referral_id(world.inviting.id))
        is None
    )
