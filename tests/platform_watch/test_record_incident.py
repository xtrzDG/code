"""
Recording an incident offers the matching status announcement: when the
admin wrote one it is published after the incident and linked to it; a
refused announcement leaves the incident recorded and unlinked.
"""

import pytest

from app.orchestrators.reliability.record_incident_orchestrator import (
    RecordIncidentOrchestrator,
)
from app.schemas.constants.platform_status import (
    AnnouncementLevel,
    StatusComponent,
)
from app.schemas.dto.incidents import (
    CreateIncidentCommand,
    LinkIncidentAnnouncementCommand,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.incidents.prefixed_id import IncidentId
from app.schemas.typings.platform_status.prefixed_id import AnnouncementId
from app.use_cases.admin.incidents.link_incident_announcement_use_case import (
    LinkIncidentAnnouncementUseCase,
)
from app.use_cases.platform_status.create_announcement_use_case import (
    CreateAnnouncementUseCase,
)
from tests.platform_ops.incident_world import IncidentWorld, breach
from tests.platform_ops.ops_documents import HOUR, at
from tests.platform_ops.ops_world import AdminsOnly

SLOW_REPLIES: dict[str, object] = {
    "level": "degraded",
    "components": ["chat", "telegram"],
    "messages": [
        {"language": "en", "text": "Replies are slow; we are on it."},
        {"language": "ru", "text": "Ответы задерживаются, мы чиним."},
    ],
}


def recorder(world: IncidentWorld) -> RecordIncidentOrchestrator:
    return RecordIncidentOrchestrator(
        create_incident=world.use_case,
        create_announcement=CreateAnnouncementUseCase(
            AdminsOnly(),
            world.announcement_repo,
            world.audit_repo,
            world.step_up,
            world.clock.wall_clock,
        ),
        link_announcement=LinkIncidentAnnouncementUseCase(
            world.incident_repo, world.clock.wall_clock
        ),
    )


def outage(**changes: object) -> CreateIncidentCommand:
    return breach(kind="outage", notice_texts=[], **changes)


def test_the_announcement_is_published_and_linked_to_the_incident() -> None:
    world = IncidentWorld()

    view = recorder(world).execute(
        outage(scope="all_businesses", announcement=SLOW_REPLIES)
    )

    [announcement] = world.announcements.list_all()
    assert view.announcement_id == announcement.id
    assert announcement.level is AnnouncementLevel.DEGRADED
    assert announcement.components == [
        StatusComponent.CHAT,
        StatusComponent.TELEGRAM,
    ]
    [stored] = world.incidents.list_all()
    assert stored.announcement_id == announcement.id
    assert view.is_expanding


def test_without_an_announcement_only_the_incident_is_recorded() -> None:
    world = IncidentWorld()

    view = recorder(world).execute(outage(affected_business_ids=[str(world.salon.id)]))

    assert view.announcement_id is None
    assert world.announcements.list_all() == []
    assert len(world.incidents.list_all()) == 1


def test_a_refused_announcement_leaves_the_incident_recorded() -> None:
    world = IncidentWorld()
    ended = {**SLOW_REPLIES, "expected_end_at": int(at(-HOUR))}

    with pytest.raises(ValidationFailedError):
        recorder(world).execute(
            outage(affected_business_ids=[str(world.salon.id)], announcement=ended)
        )

    [stored] = world.incidents.list_all()
    assert stored.announcement_id is None
    assert world.announcements.list_all() == []


def test_linking_an_unknown_incident_is_refused() -> None:
    world = IncidentWorld()

    with pytest.raises(NotFoundError):
        LinkIncidentAnnouncementUseCase(
            world.incident_repo, world.clock.wall_clock
        ).run(
            LinkIncidentAnnouncementCommand(
                incident_id=IncidentId(), announcement_id=AnnouncementId()
            )
        )
