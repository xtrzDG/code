"""An owner's side of the referral program: the invitation and "Powered by"."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.analytics.constrained_strings import ReferralCode
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.referrals.booleans import (
    IsInviteCardDue,
    IsPoweredByHidden,
    IsPoweredByRemovable,
    IsPoweredByShown,
)
from app.schemas.typings.referrals.constrained_integers import ReferredBusinessCount
from app.schemas.typings.referrals.constrained_strings import ReferralLink
from app.schemas.typings.users.prefixed_id import UserId


class ReferralProgramQuery(ImmutableDTO):
    """An owner opens their business's invitation."""

    user_id: UserId
    business_id: BusinessId


class PoweredByView(ImmutableDTO):
    """
    The "Powered by" link of the chat, the hosted page and the table card:
    whether it is shown, whether the plan lets the owner remove it (Plus),
    the owner's choice and the link itself (None while it is not shown).
    """

    is_shown: IsPoweredByShown
    is_removable: IsPoweredByRemovable
    is_hidden: IsPoweredByHidden
    url: ReferralLink | None = None


class ReferralProgramView(ImmutableDTO):
    """
    The business's invitation ("Invite a business: a month free"): its own
    code and link, how many businesses signed up by it, paid and earned
    both sides their month, how many bookings the business has had (the
    card appears from the tenth: `is_invite_card_due`), and the "Powered
    by" link.
    """

    code: ReferralCode | None = None
    invite_link: ReferralLink | None = None
    invited: ReferredBusinessCount
    paid: ReferredBusinessCount
    rewarded: ReferredBusinessCount
    bookings_made: PeriodItemCount
    invite_card_min_bookings: PeriodItemCount
    is_invite_card_due: IsInviteCardDue
    powered_by: PoweredByView


class PoweredByRequest(ImmutableDTO):
    """
    HTTP body of a Plus owner's choice to leave the "Powered by" link off.

    Example: {"is_hidden": true}.
    """

    is_hidden: IsPoweredByHidden


class PoweredByCommand(ImmutableDTO):
    """An owner shows or hides the "Powered by" link (Plus only)."""

    user_id: UserId
    business_id: BusinessId
    request: PoweredByRequest
