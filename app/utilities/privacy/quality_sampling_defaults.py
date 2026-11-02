"""
Whether the nightly quality sample may read a business's conversations
before its owner chose (Settings → Privacy): privacy by default (GDPR art.
25) for every business created from 3 November 2026 on, so only its owner
turns the sample on. A business created before keeps what it had: on,
unless its owner turned it off (its choice is stored then).
"""

from typed_time_provider import Microseconds

from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.privacy.booleans import IsQualitySamplingAllowed
from app.utilities.privacy.retention_keys import privacy_settings_id_of

# 2026-11-03T00:00:00Z: businesses created from then on start with it off.
QUALITY_SAMPLING_OFF_FOR_BUSINESSES_FROM: Microseconds = Microseconds(
    1_793_664_000_000_000
)


def default_quality_sampling(business: BusinessDocument) -> IsQualitySamplingAllowed:
    """Off for a business created from the cut-off on, on for an older one."""

    return int(business.created_at) < int(QUALITY_SAMPLING_OFF_FOR_BUSINESSES_FROM)


def default_privacy_settings(
    business: BusinessDocument,
) -> BusinessPrivacySettingsDocument:
    """The settings of a business whose owner never saved any."""

    return BusinessPrivacySettingsDocument(
        id=privacy_settings_id_of(business.id),
        business_id=business.id,
        quality_sampling_allowed=default_quality_sampling(business),
    )
