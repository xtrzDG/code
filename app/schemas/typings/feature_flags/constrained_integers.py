"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class FeatureFlagBucket(BaseConstrainedTypedInt):
    """
    Where a business falls in a flag's rollout, 0 to 99: a stable hash of
    the flag and the business, so a business keeps its answer while the
    percentage only grows.
    """

    ge = 0
    le = 99


class FeatureFlagRolloutPercent(BaseConstrainedTypedInt):
    """
    The share of businesses a switched-on feature flag holds for, 0 to 100
    (the businesses whose bucket is below it), besides those it names.
    """

    ge = 0
    le = 100
