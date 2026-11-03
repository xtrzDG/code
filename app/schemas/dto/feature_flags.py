"""The feature flags of staged rollouts, for the platform admin (REL-08)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.feature_flags import FeatureFlagDecision
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.feature_flags.booleans import (
    IsFeatureFlagEnabled,
    IsFeatureFlagOn,
)
from app.schemas.typings.feature_flags.constrained_integers import (
    FeatureFlagBucket,
    FeatureFlagRolloutPercent,
)
from app.schemas.typings.feature_flags.constrained_strings import (
    FeatureFlagChangeReason,
    FeatureFlagName,
)
from app.schemas.typings.feature_flags.strings import FeatureFlagDescription
from app.schemas.typings.users.prefixed_id import UserId


class FeatureFlagListQuery(ImmutableDTO):
    user_id: UserId


class FeatureFlagView(ImmutableDTO):
    """
    A flag of the registry as it stands: off with no lists until first set
    (`changed_*` None).
    """

    name: FeatureFlagName
    description: FeatureFlagDescription
    is_enabled: IsFeatureFlagEnabled
    rollout_percent: FeatureFlagRolloutPercent
    included_business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])
    excluded_business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])
    reason: FeatureFlagChangeReason | None = None
    changed_by: UserId | None = None
    changed_at: Microseconds | None = None


class FeatureFlagList(ImmutableDTO):
    items: list[FeatureFlagView] = Field(default_factory=list[FeatureFlagView])


class FeatureFlagRequest(ImmutableDTO):
    """
    Body of PUT /v1/admin/feature-flags/{flag_name}: the whole new state of
    the flag and why (the audit log keeps the reason).
    """

    is_enabled: IsFeatureFlagEnabled
    rollout_percent: FeatureFlagRolloutPercent
    included_business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])
    excluded_business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])
    reason: FeatureFlagChangeReason


class FeatureFlagCommand(ImmutableDTO):
    """A SUPER platform admin sets a flag of the registry."""

    user_id: UserId
    name: FeatureFlagName
    request: FeatureFlagRequest
    client_ip_address: ClientIpAddress | None = None


class FeatureFlagCheckQuery(ImmutableDTO):
    user_id: UserId
    name: FeatureFlagName
    business_id: BusinessId


class FeatureFlagCheck(ImmutableDTO):
    """
    Whether the flag holds for the business now, as the release's code
    sees it, why, and the business's bucket in its rollout (0-99).
    """

    name: FeatureFlagName
    business_id: BusinessId
    is_on: IsFeatureFlagOn
    decision: FeatureFlagDecision
    bucket: FeatureFlagBucket
