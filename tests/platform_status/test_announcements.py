"""
The admin's announcements: only operations admins, after a recent sign-in,
audited platform-wide; resolved ones cannot change; the list pages.
"""

import pytest
from pydantic import ValidationError
from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.platform_status import (
    AnnouncementLevel,
    AnnouncementStatus,
    StatusComponent,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.dto.platform_announcements import (
    AnnouncementAdminView,
    AnnouncementMessageInput,
    AnnouncementsQuery,
    CreateAnnouncementBody,
    CreateAnnouncementCommand,
    UpdateAnnouncementBody,
    UpdateAnnouncementCommand,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform_status.constrained_strings import AnnouncementText
from app.schemas.typings.platform_status.prefixed_id import AnnouncementId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.platform_status.create_announcement_use_case import (
    CreateAnnouncementUseCase,
)
from app.use_cases.platform_status.list_announcements_use_case import (
    ListAnnouncementsUseCase,
)
from app.use_cases.platform_status.update_announcement_use_case import (
    UpdateAnnouncementUseCase,
)
from tests.platform_ops.ops_world import ADMIN, AdminsOnly
from tests.platform_ops.test_incidents import StepUp
from tests.platform_status.status_world import DAY, HOUR, StatusWorld

IP = ClientIpAddress("203.0.113.7")
META = [StatusComponent.META]


def texts(**languages: str) -> list[AnnouncementMessageInput]:
    return [
        AnnouncementMessageInput(
            language=LanguageTag(language), text=AnnouncementText(text)
        )
        for language, text in languages.items()
    ]


ENGLISH = texts(en="Replies in WhatsApp are slow.", ka="WhatsApp-ში პასუხები ნელია.")


def outage(**changes: object) -> CreateAnnouncementBody:
    fields: dict[str, object] = {
        "level": AnnouncementLevel.OUTAGE,
        "components": META,
        "messages": ENGLISH,
    }
    return CreateAnnouncementBody.model_validate({**fields, **changes})


def create(
    world: StatusWorld,
    body: CreateAnnouncementBody,
    user: UserId = ADMIN,
    is_recent: bool = True,
) -> AnnouncementAdminView:
    return CreateAnnouncementUseCase(
        AdminsOnly(),
        world.announcement_repo,
        world.audit_repo,
        StepUp(is_recent),
        world.clock.wall_clock,
    ).run(CreateAnnouncementCommand(user_id=user, body=body, client_ip_address=IP))


def update(
    world: StatusWorld,
    announcement_id: AnnouncementId,
    body: UpdateAnnouncementBody,
    is_recent: bool = True,
) -> AnnouncementAdminView:
    return UpdateAnnouncementUseCase(
        AdminsOnly(),
        world.announcement_repo,
        world.audit_repo,
        StepUp(is_recent),
        world.clock.wall_clock,
    ).run(
        UpdateAnnouncementCommand(
            user_id=ADMIN,
            announcement_id=announcement_id,
            body=body,
            client_ip_address=IP,
        )
    )


def test_an_announcement_is_stored_and_audited_platform_wide() -> None:
    world = StatusWorld()

    view = create(world, outage())

    assert view.status is AnnouncementStatus.ACTIVE
    assert view.starts_at == world.now
    assert [str(message.language) for message in view.messages] == ["en", "ka"]
    [entry] = world.audit.list_all()
    assert (entry.action, str(entry.entity), str(entry.entity_id)) == (
        AuditAction.CREATE,
        "platform_announcement",
        str(view.id),
    )
    assert entry.business_id is None and entry.ip_address == IP


def test_only_operations_admins_announce_after_a_recent_sign_in() -> None:
    world = StatusWorld()

    with pytest.raises(AccessDeniedError):
        create(world, outage(), user=UserId())
    with pytest.raises(StepUpRequiredError):
        create(world, outage(), is_recent=False)
    assert world.announcements.list_all() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"messages": texts(ru="Задержки.")},
        {"messages": [*ENGLISH, *texts(en="Again.")]},
        {"components": []},
        {"components": [StatusComponent.META, StatusComponent.META]},
        {"starts_at": 10, "expected_end_at": 5},
    ],
)
def test_a_body_needs_english_components_and_a_sane_window(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        outage(**changes)


def test_a_notice_may_name_no_component() -> None:
    body = outage(level=AnnouncementLevel.INFO, components=[])

    assert create(StatusWorld(), body).components == []


def test_maintenance_is_planned_within_sixty_days_and_ends_after_now() -> None:
    world = StatusWorld()
    planned = create(
        world,
        outage(level=AnnouncementLevel.MAINTENANCE, starts_at=world.now + DAY),
    )

    assert planned.starts_at == world.now + DAY
    with pytest.raises(ValidationFailedError, match="60 days"):
        create(world, outage(starts_at=world.now + 61 * DAY))
    with pytest.raises(ValidationFailedError, match="after now"):
        create(
            world, outage(starts_at=world.now - DAY, expected_end_at=world.now - HOUR)
        )


def test_the_team_updates_then_resolves_an_announcement() -> None:
    world = StatusWorld()
    created = create(world, outage())
    world.clock.advance(HOUR)

    changed = update(
        world,
        created.id,
        UpdateAnnouncementBody(
            level=AnnouncementLevel.DEGRADED,
            messages=texts(en="Recovering, replies come within minutes."),
            expected_end_at=Microseconds(world.now + HOUR),
        ),
    )
    world.clock.advance(HOUR)
    resolved = update(world, created.id, UpdateAnnouncementBody(resolve=True))

    assert changed.level is AnnouncementLevel.DEGRADED
    assert changed.components == META
    assert changed.updated_by == ADMIN and changed.resolved_at is None
    assert resolved.status is AnnouncementStatus.RESOLVED
    assert resolved.resolved_at == world.now
    assert resolved.messages == changed.messages
    assert [entry.action for entry in world.audit.list_all()] == [
        AuditAction.CREATE,
        AuditAction.UPDATE,
        AuditAction.UPDATE,
    ]
    with pytest.raises(ConflictError):
        update(world, created.id, UpdateAnnouncementBody(resolve=True))


def test_an_update_keeps_components_for_levels_that_need_them() -> None:
    world = StatusWorld()
    created = create(world, outage(level=AnnouncementLevel.INFO, components=[]))

    with pytest.raises(ValidationFailedError):
        update(
            world, created.id, UpdateAnnouncementBody(level=AnnouncementLevel.OUTAGE)
        )
    with pytest.raises(ValidationFailedError):
        update(
            world,
            created.id,
            UpdateAnnouncementBody(expected_end_at=Microseconds(world.now - HOUR)),
        )
    with pytest.raises(NotFoundError):
        update(world, AnnouncementId(), UpdateAnnouncementBody(resolve=True))
    with pytest.raises(StepUpRequiredError):
        update(world, created.id, UpdateAnnouncementBody(resolve=True), is_recent=False)
    with pytest.raises(ValidationError):
        UpdateAnnouncementBody()
    with pytest.raises(ValidationError):
        UpdateAnnouncementBody(components=META * 2)
    with pytest.raises(ValidationError):
        UpdateAnnouncementBody(messages=texts(ru="Только по-русски."))


def test_the_list_pages_newest_first() -> None:
    world = StatusWorld()
    first = create(world, outage())
    world.clock.advance(HOUR)
    second = create(world, outage())
    listing = ListAnnouncementsUseCase(AdminsOnly(), world.announcement_repo)

    page = listing.run(
        AnnouncementsQuery(user_id=ADMIN, page=PageRequest.model_validate({"size": 1}))
    )
    rest = listing.run(
        AnnouncementsQuery(
            user_id=ADMIN,
            page=PageRequest.model_validate({"size": 1, "cursor": page.next_cursor}),
        )
    )

    assert [item.id for item in page.items] == [second.id]
    assert [item.id for item in rest.items] == [first.id]
    with pytest.raises(AccessDeniedError):
        listing.run(AnnouncementsQuery(user_id=UserId(), page=PageRequest()))
