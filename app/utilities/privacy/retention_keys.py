"""
The derived ids of the retention engine: one privacy settings document
and one purge state per business.
"""

from uuid import UUID, uuid5

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.prefixed_id import (
    BusinessPrivacySettingsId,
    RetentionPurgeStateId,
)

# Fixed namespaces of derived ids (never change them: stored ids depend on
# them).
PRIVACY_SETTINGS_NAMESPACE: UUID = UUID("84e4d56e-abdb-4da4-ba1e-c04be68a15cc")
RETENTION_PURGE_STATE_NAMESPACE: UUID = UUID("956d86f2-5565-4cdf-97a8-84fd1ae3164a")


def privacy_settings_id_of(business_id: BusinessId) -> BusinessPrivacySettingsId:
    """One privacy settings document per business."""

    return BusinessPrivacySettingsId(
        uuid5(PRIVACY_SETTINGS_NAMESPACE, str(business_id))
    )


def retention_purge_state_id_of(business_id: BusinessId) -> RetentionPurgeStateId:
    """One retention purge state per business."""

    return RetentionPurgeStateId(
        uuid5(RETENTION_PURGE_STATE_NAMESPACE, str(business_id))
    )
