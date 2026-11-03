from base_pydantic_schemas import BaseDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.feature_flags.booleans import IsFeatureFlagEnabled
from app.schemas.typings.feature_flags.constrained_integers import (
    FeatureFlagRolloutPercent,
)
from app.schemas.typings.feature_flags.constrained_strings import (
    FeatureFlagChangeReason,
    FeatureFlagName,
)
from app.schemas.typings.users.prefixed_id import UserId


class FeatureFlagDocument(BaseDocument):
    """
    One feature flag of a risky release (a platform collection, one row per
    flag stored under its name, migration 1260; REL-08): whether it is
    switched on, for which share of the businesses (`rollout_percent`: those
    whose stable bucket of the flag and the business is below it), which
    businesses get it anyway (`included_business_ids`) and which never do
    (`excluded_business_ids`, which wins). Read at request time through the
    flag gate; a flag never set is off. `reason`, `changed_by` and
    `changed_at` name the last change, which the audit log keeps too.
    """

    schema_version: SchemaVersion = SchemaVersion("1")
    name: FeatureFlagName
    is_enabled: IsFeatureFlagEnabled
    rollout_percent: FeatureFlagRolloutPercent
    included_business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])
    excluded_business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])
    reason: FeatureFlagChangeReason
    changed_by: UserId
    changed_at: Microseconds
