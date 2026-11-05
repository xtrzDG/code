from enum import StrEnum


class FeatureFlagDecision(StrEnum):
    """
    Why a feature flag holds for a business or not (an answer, never
    stored):

    - OFF: the flag is switched off (or was never set): nobody gets it.
    - EXCLUDED: switched on, but the business is on its exclusion list.
    - INCLUDED: switched on and the business is on its inclusion list.
    - IN_ROLLOUT: switched on and the business's bucket is below the
      rollout percentage.
    - OUTSIDE_ROLLOUT: switched on, but the bucket is not below it.
    """

    OFF = "off"
    EXCLUDED = "excluded"
    INCLUDED = "included"
    IN_ROLLOUT = "in_rollout"
    OUTSIDE_ROLLOUT = "outside_rollout"
