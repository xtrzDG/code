from base_pydantic_schemas import BaseDocument, SchemaVersion
from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import (
    AlertUnit,
    PlatformAlertCode,
    PlatformAlertStatus,
)
from app.schemas.typings.monitoring.constrained_integers import (
    AlertFigure,
    AlertThreshold,
    NotificationCount,
)
from app.schemas.typings.monitoring.strings import AlertDetailText


class PlatformAlertStateDocument(BaseDocument):
    """
    The latest episode of one platform alert, stored under its code (a
    platform collection: no business owns it).

    An episode starts when the alert's check first fires (`fired_at`) and
    ends when a check no longer fires (`resolved_at`). The team is told
    when it starts, again after each cooldown while it still fires
    (`notified_at`, `notification_count`) and once when it is over. The
    figure, the threshold it was compared with, their unit and the detail
    are those of the latest check, for the admin system page.
    """

    # 2: `code` may be `quality_drop` (production quality, migration 1120).
    schema_version: SchemaVersion = SchemaVersion("2")
    code: PlatformAlertCode
    status: PlatformAlertStatus
    figure: AlertFigure
    threshold: AlertThreshold
    unit: AlertUnit
    detail: AlertDetailText
    fired_at: Microseconds
    checked_at: Microseconds
    notified_at: Microseconds | None = None
    notification_count: NotificationCount = NotificationCount(0)
    resolved_at: Microseconds | None = None
