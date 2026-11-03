"""
The registry of feature flags (REL-08, docs/operations/deploys.md, "Staged
rollouts"): every flag a release may read, with what it guards. A risky
change ships behind a flag of its own, switched on for a few businesses
(by name, or a percentage of them), widened step by step while its
alerts and budgets stay quiet, and removed with the old path once it holds
for everyone. The admin sets a flag only if it is listed here; a flag
never set is off.
"""

from dataclasses import dataclass

from app.schemas.typings.feature_flags.constrained_strings import FeatureFlagName
from app.schemas.typings.feature_flags.strings import FeatureFlagDescription


@dataclass(frozen=True)
class FeatureFlagDefinition:
    name: FeatureFlagName
    description: FeatureFlagDescription


RELEASE_CANARY: FeatureFlagName = FeatureFlagName("release_canary")

FEATURE_FLAGS: tuple[FeatureFlagDefinition, ...] = (
    # The rollout check of the deploy runbook: switched on for one
    # business, then a percentage, to see the gate answer exactly as set
    # before a risky change leans on a flag of its own.
    FeatureFlagDefinition(
        RELEASE_CANARY,
        FeatureFlagDescription(
            "Rollout check: guards nothing; shows that a staged rollout "
            "reaches exactly the businesses it names and its percentage."
        ),
    ),
)


def find_feature_flag(name: str) -> FeatureFlagDefinition | None:
    """The registry's flag of that name; None for any other name."""

    return next(
        (definition for definition in FEATURE_FLAGS if str(definition.name) == name),
        None,
    )
