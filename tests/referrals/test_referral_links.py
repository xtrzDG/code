"""A business's own code: claimed once, stable, never a partner's."""

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.referrals import (
    POWERED_BY_SOURCE_TAG,
    ReferralCodeOwnerKind,
)
from app.schemas.domain.referrals import ReferralCodeDocument
from app.utilities.referrals.invite_card import (
    INVITE_CARD_MIN_BOOKINGS,
    is_invite_card_due,
)
from app.utilities.referrals.referral_identity import (
    business_code_candidates,
    partner_id_for,
    referral_code_id,
)
from tests.billing.billing_testbed import BillingTestbed
from tests.referrals.referral_parts import CABINET_BASE_URL


def test_a_business_code_is_claimed_once_and_stays() -> None:
    testbed = BillingTestbed()
    business = testbed.add_business(testbed.add_user(email="owner@example.com"))
    links = testbed.referrals.links(testbed.clock.wall_clock)

    code = links.business_code(business.id)

    assert code is not None
    assert code == business_code_candidates(business.id)[0]
    assert links.business_code(business.id) == code
    stored = testbed.referrals.referral_code_repo.get(referral_code_id(code))
    assert stored is not None
    assert stored.owner_kind is ReferralCodeOwnerKind.BUSINESS
    assert stored.business_id == business.id


def test_a_code_a_partner_holds_is_skipped_for_the_longer_one() -> None:
    testbed = BillingTestbed()
    business = testbed.add_business(testbed.add_user(email="owner@example.com"))
    short, longer = business_code_candidates(business.id)
    testbed.referrals.referral_code_repo.claim(
        ReferralCodeDocument(
            id=referral_code_id(short),
            code=short,
            owner_kind=ReferralCodeOwnerKind.PARTNER,
            partner_id=partner_id_for("email:partner@example.com"),
        )
    )

    links = testbed.referrals.links(testbed.clock.wall_clock)

    assert links.business_code(business.id) == longer


def test_links_need_the_site_address() -> None:
    testbed = BillingTestbed()
    business = testbed.add_business(testbed.add_user(email="owner@example.com"))

    without_site = testbed.referrals.links(testbed.clock.wall_clock, None)
    with_site = testbed.referrals.links(testbed.clock.wall_clock)

    assert without_site.link_for(business.id, POWERED_BY_SOURCE_TAG) is None
    code = with_site.business_code(business.id)
    assert with_site.link_for(business.id, POWERED_BY_SOURCE_TAG) == (
        f"{CABINET_BASE_URL}/?ref={code}&src=powered_by"
    )


def test_a_hidden_link_shows_again_when_the_business_leaves_plus() -> None:
    testbed = BillingTestbed()
    business = testbed.add_business(
        testbed.add_user(email="owner@example.com"), plan_key=PlanKey.PLUS
    )
    business.hides_powered_by = True
    links = testbed.referrals.links(testbed.clock.wall_clock)

    assert links.powered_by_link(business, POWERED_BY_SOURCE_TAG) is None

    business.plan_key = PlanKey.CHAT
    assert links.powered_by_link(business, POWERED_BY_SOURCE_TAG) is not None


def test_the_invitation_card_comes_with_the_tenth_booking() -> None:
    assert INVITE_CARD_MIN_BOOKINGS == 10
    assert is_invite_card_due(9) is False  # type: ignore[arg-type]
    assert is_invite_card_due(10) is True  # type: ignore[arg-type]
