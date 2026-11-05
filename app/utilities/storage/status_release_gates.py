"""
The release gate of the status page's payments component (REL-06).

This release reads `payments` in the stored announcements and status days
and shows the component's level now (from the alerts that affect
payments); the day records and announcements that name it are written
once the next release opens the gate, when the release before it reads
the value too. Until then its history shows no data and an admin cannot
announce it yet.
"""

from app.schemas.dto.release_gates import ReleaseGate
from app.schemas.typings.maintenance.constrained_strings import (
    GatedEnumValue,
    ReleaseGateName,
    StoredEnumPath,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName

PAYMENTS_STATUS_GATE: ReleaseGateName = ReleaseGateName("status_payments")
PAYMENTS_COMPONENT: GatedEnumValue = GatedEnumValue("payments")

STATUS_RELEASE_GATES: tuple[ReleaseGate, ...] = (
    ReleaseGate(
        name=PAYMENTS_STATUS_GATE,
        collection_name=DocumentCollectionName("platform_announcements"),
        path=StoredEnumPath("components[]"),
        values=[PAYMENTS_COMPONENT],
        is_open=False,
    ),
    ReleaseGate(
        name=PAYMENTS_STATUS_GATE,
        collection_name=DocumentCollectionName("platform_status_days"),
        path=StoredEnumPath("components[].component"),
        values=[PAYMENTS_COMPONENT],
        is_open=False,
    ),
)
