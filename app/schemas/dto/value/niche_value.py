"""What a niche's assistant typically saves and earns, before the owner says more."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.niches import NicheKey
from app.schemas.dto.billing import Money
from app.schemas.typings.value.constrained_integers import (
    StaffSecondsPerCall,
    StaffSecondsPerReply,
)


class NicheValueDefaults(ImmutableDTO):
    """
    The estimates of one niche: what a booking (or order) typically brings
    (`typical_check`, in euro; None where checks vary too much to guess,
    e.g. real estate), and how long staff would take to write one reply
    and to answer one phone call.
    """

    niche_key: NicheKey
    typical_check: Money | None = None
    seconds_per_reply: StaffSecondsPerReply
    seconds_per_call: StaffSecondsPerCall
