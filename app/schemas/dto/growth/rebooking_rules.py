"""A niche's default rebooking rule (Bookings → Return visits starts from it)."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.campaigns import RebookingRuleKind
from app.schemas.constants.niches import NicheKey
from app.schemas.typings.campaigns.constrained_integers import RebookingDelayDays


class RebookingRule(ImmutableDTO):
    """
    What a niche's campaign sends and when: an invitation back after the
    last visit (a salon after five weeks), a recall when a regular check
    is due (a clinic after half a year), or practical details before an
    arrival (a hotel two days ahead).
    """

    niche_key: NicheKey
    rule_kind: RebookingRuleKind
    delay_days: RebookingDelayDays
