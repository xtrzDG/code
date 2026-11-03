"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class FeatureFlagChangeReason(BaseConstrainedTypedString):
    """
    Why a platform admin changed a feature flag (a rollout step, a stop),
    in their own words; the audit log keeps it with the change.

    Example:
        reason = FeatureFlagChangeReason("10% after a clean day at 1%")
    """

    min_length = 8
    max_length = 300
    pattern = r"^\S[\s\S]*\S$"


class FeatureFlagName(BaseConstrainedTypedString):
    """
    The name of a feature flag of the registry (feature_flag_catalog), as
    stored and as the routes take it: lower-case words joined by `_`.

    Example:
        name = FeatureFlagName("release_canary")
    """

    pattern = r"^[a-z][a-z0-9_]{2,62}$"
