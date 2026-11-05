"""
Whether a feature flag holds for a business (REL-08): pure functions over
the stored flag, read at request time by the flag gate.

Off unless switched on; then a business on the exclusion list never gets
it, one on the inclusion list always does, and any other gets it when its
bucket (0-99, a SHA-256 of the flag's name and the business id) is below
the rollout percentage. The bucket is stable, so raising the percentage
only adds businesses and lowering it only removes some: nobody flips back
and forth while a rollout widens.
"""

import hashlib

from app.schemas.constants.feature_flags import FeatureFlagDecision
from app.schemas.domain.feature_flags import FeatureFlagDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.feature_flags.constrained_integers import FeatureFlagBucket
from app.schemas.typings.feature_flags.constrained_strings import FeatureFlagName

BUCKETS: int = 100
HOLDING_DECISIONS: frozenset[FeatureFlagDecision] = frozenset(
    {FeatureFlagDecision.INCLUDED, FeatureFlagDecision.IN_ROLLOUT}
)


def rollout_bucket(name: FeatureFlagName, business_id: BusinessId) -> FeatureFlagBucket:
    """The business's stable place, 0-99, in the flag's rollout."""

    digest: bytes = hashlib.sha256(f"{name}:{business_id}".encode()).digest()
    return FeatureFlagBucket(int.from_bytes(digest[:8], "big") % BUCKETS)


def decide(
    flag: FeatureFlagDocument | None, business_id: BusinessId
) -> FeatureFlagDecision:
    """Why the flag holds for the business or not."""

    if flag is None or not flag.is_enabled:
        return FeatureFlagDecision.OFF

    if business_id in flag.excluded_business_ids:
        return FeatureFlagDecision.EXCLUDED

    if business_id in flag.included_business_ids:
        return FeatureFlagDecision.INCLUDED

    bucket: int = int(rollout_bucket(flag.name, business_id))
    return (
        FeatureFlagDecision.IN_ROLLOUT
        if bucket < int(flag.rollout_percent)
        else FeatureFlagDecision.OUTSIDE_ROLLOUT
    )


def is_holding(decision: FeatureFlagDecision) -> bool:
    return decision in HOLDING_DECISIONS
