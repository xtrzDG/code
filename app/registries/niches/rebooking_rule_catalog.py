"""
Each niche's default rebooking rule: what its campaign sends and when, as
an owner of such a business would set it. The owner can change both in
Bookings → Return visits.

- Invitations back after the last visit: haircuts and nails (five weeks),
  classes and lessons (two weeks), restaurants and entertainment (a month
  or six weeks), shops and suppliers (a reorder after one or two months).
- Recalls when a regular check is due: clinics and home services (half a
  year), car services (half a year), vets (a year: vaccinations).
- Practical details before an arrival: hotels and rentals two days ahead,
  car rentals and tours, venues a few days ahead.
"""

from app.schemas.constants.campaigns import RebookingRuleKind
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.growth.rebooking_rules import RebookingRule
from app.schemas.typings.campaigns.constrained_integers import RebookingDelayDays


def _rule(niche_key: NicheKey, kind: RebookingRuleKind, days: int) -> RebookingRule:
    return RebookingRule(
        niche_key=niche_key, rule_kind=kind, delay_days=RebookingDelayDays(days)
    )


REBOOK: RebookingRuleKind = RebookingRuleKind.REBOOK
RECALL: RebookingRuleKind = RebookingRuleKind.RECALL
PRE_ARRIVAL: RebookingRuleKind = RebookingRuleKind.PRE_ARRIVAL

NICHE_REBOOKING_RULES: tuple[RebookingRule, ...] = (
    _rule(NicheKey.RESTAURANT, REBOOK, 30),
    _rule(NicheKey.HOTEL, PRE_ARRIVAL, 2),
    _rule(NicheKey.ENTERTAINMENT, REBOOK, 45),
    _rule(NicheKey.BEAUTY_SALON, REBOOK, 35),
    _rule(NicheKey.CLINIC, RECALL, 180),
    _rule(NicheKey.FITNESS, REBOOK, 14),
    _rule(NicheKey.SHORT_TERM_RENTAL, PRE_ARRIVAL, 2),
    _rule(NicheKey.CAR_SERVICE, RECALL, 180),
    _rule(NicheKey.CAR_RENTAL_AND_TOURS, PRE_ARRIVAL, 1),
    _rule(NicheKey.EVENT_VENUE, PRE_ARRIVAL, 3),
    _rule(NicheKey.REAL_ESTATE, REBOOK, 30),
    _rule(NicheKey.EDUCATION, REBOOK, 14),
    _rule(NicheKey.ONLINE_SHOP, REBOOK, 60),
    _rule(NicheKey.VETERINARY, RECALL, 365),
    _rule(NicheKey.HOME_SERVICES, RECALL, 180),
    _rule(NicheKey.B2B_SUPPLY, REBOOK, 30),
)
