"""The status page's collections in memory, a movable clock and documents."""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.platform_alert_state_repository import (
    PlatformAlertStateRepository,
)
from app.repositories.platform_announcement_repository import (
    PlatformAnnouncementRepository,
)
from app.repositories.platform_status_day_repository import (
    PlatformStatusDayRepository,
)
from app.schemas.constants.monitoring import (
    AlertUnit,
    PlatformAlertCode,
    PlatformAlertStatus,
)
from app.schemas.constants.platform_status import (
    AnnouncementLevel,
    StatusComponent,
)
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.domain.platform_status import (
    AnnouncementMessage,
    PlatformAnnouncementDocument,
    PlatformStatusDayDocument,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.monitoring.constrained_integers import (
    AlertFigure,
    AlertThreshold,
)
from app.schemas.typings.monitoring.strings import AlertDetailText
from app.schemas.typings.platform_status.constrained_strings import AnnouncementText
from app.schemas.typings.users.prefixed_id import UserId
from tests.platform_ops.ops_world import ADMIN, OpsClock

MINUTE: int = 60 * 1_000_000
HOUR: int = 60 * MINUTE
DAY: int = 24 * HOUR


def alert(
    code: PlatformAlertCode,
    figure: int,
    checked_at: int,
    status: PlatformAlertStatus = PlatformAlertStatus.FIRING,
) -> PlatformAlertStateDocument:
    return PlatformAlertStateDocument(
        code=code,
        status=status,
        figure=AlertFigure(figure),
        threshold=AlertThreshold(10),
        unit=AlertUnit.PERCENT,
        detail=AlertDetailText("Detail."),
        fired_at=Microseconds(checked_at),
        checked_at=Microseconds(checked_at),
    )


def announcement(
    level: AnnouncementLevel,
    components: list[StatusComponent],
    starts_at: int,
    texts: dict[str, str] | None = None,
    created_by: UserId = ADMIN,
) -> PlatformAnnouncementDocument:
    messages = texts or {"en": "WhatsApp replies are delayed.", "ru": "Задержки."}
    return PlatformAnnouncementDocument(
        level=level,
        components=components,
        messages=[
            AnnouncementMessage(
                language=LanguageTag(language), text=AnnouncementText(text)
            )
            for language, text in messages.items()
        ],
        starts_at=Microseconds(starts_at),
        created_by=created_by,
        created_at=Microseconds(starts_at),
        updated_at=Microseconds(starts_at),
    )


class StatusWorld:
    def __init__(self) -> None:
        self.clock = OpsClock()
        self.alert_states = InMemoryDocumentCollectionAdapter[
            PlatformAlertStateDocument
        ](PlatformAlertStateDocument)
        self.announcements = InMemoryDocumentCollectionAdapter[
            PlatformAnnouncementDocument
        ](PlatformAnnouncementDocument)
        self.days = InMemoryDocumentCollectionAdapter[PlatformStatusDayDocument](
            PlatformStatusDayDocument
        )
        self.audit = InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](
            AuditLogEntryDocument
        )
        self.alert_repo = PlatformAlertStateRepository(self.alert_states)
        self.announcement_repo = PlatformAnnouncementRepository(self.announcements)
        self.day_repo = PlatformStatusDayRepository(self.days)
        self.audit_repo = AuditLogRepository(self.audit)

    @property
    def now(self) -> int:
        return self.clock.now

    def fire(self, code: PlatformAlertCode, figure: int) -> None:
        self.alert_repo.save(alert(code, figure, self.now))

    def resolve(self, code: PlatformAlertCode) -> None:
        self.alert_repo.save(alert(code, 0, self.now, PlatformAlertStatus.RESOLVED))

    def announce(
        self,
        level: AnnouncementLevel,
        components: list[StatusComponent],
        starts_in: int = 0,
    ) -> PlatformAnnouncementDocument:
        document = announcement(level, components, self.now + starts_in)
        self.announcement_repo.save(document)
        return document
