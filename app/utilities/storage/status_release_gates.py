"""
The release gate of the status page's payments component (REL-06).

Open from this release (the release before it reads `payments` in the
stored announcements and status days): the day records name payments, so
its history fills from the deploy day on, and an admin may announce it.
Its level comes from the alerts that affect payments (no provider is
called), whether or not a provider can take payments yet.
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
        is_open=True,
    ),
    ReleaseGate(
        name=PAYMENTS_STATUS_GATE,
        collection_name=DocumentCollectionName("platform_status_days"),
        path=StoredEnumPath("components[].component"),
        values=[PAYMENTS_COMPONENT],
        is_open=True,
    ),
)
