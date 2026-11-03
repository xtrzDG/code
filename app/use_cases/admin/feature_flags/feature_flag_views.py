"""The admin's view of a registry flag: its definition and stored state."""

from app.schemas.domain.feature_flags import FeatureFlagDocument
from app.schemas.dto.feature_flags import FeatureFlagView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.feature_flags.constrained_integers import (
    FeatureFlagRolloutPercent,
)
from app.schemas.typings.feature_flags.constrained_strings import FeatureFlagName
from app.utilities.feature_flags.feature_flag_catalog import (
    FeatureFlagDefinition,
    find_feature_flag,
)

NO_ROLLOUT: FeatureFlagRolloutPercent = FeatureFlagRolloutPercent(0)


def require_definition(name: FeatureFlagName) -> FeatureFlagDefinition:
    """The registry's flag; NotFoundError for a name it does not list."""

    definition: FeatureFlagDefinition | None = find_feature_flag(str(name))
    if definition is None:
        raise NotFoundError(f"There is no feature flag {name}.")

    return definition


def build_flag_view(
    definition: FeatureFlagDefinition, flag: FeatureFlagDocument | None
) -> FeatureFlagView:
    if flag is None:
        return FeatureFlagView(
            name=definition.name,
            description=definition.description,
            is_enabled=False,
            rollout_percent=NO_ROLLOUT,
        )

    return FeatureFlagView(
        name=definition.name,
        description=definition.description,
        is_enabled=flag.is_enabled,
        rollout_percent=flag.rollout_percent,
        included_business_ids=list(flag.included_business_ids),
        excluded_business_ids=list(flag.excluded_business_ids),
        reason=flag.reason,
        changed_by=flag.changed_by,
        changed_at=flag.changed_at,
    )
