"""GET /v1/admin/incidents' use case: the log newest first, paged."""

import json

import pytest

from app.repositories.incident_repository import IncidentRepository
from app.schemas.dto.incidents import (
    CreateIncidentBody,
    CreateIncidentCommand,
    IncidentsQuery,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.incidents.list_incidents_use_case import ListIncidentsUseCase
from tests.platform_ops.ops_documents import HOUR, MINUTE, at
from tests.platform_ops.ops_world import ADMIN, AdminsOnly
from tests.platform_ops.test_incidents import IncidentWorld


def outage(world: IncidentWorld, title: str) -> CreateIncidentCommand:
    body = {
        "kind": "degradation",
        "severity": "sev3",
        "title": title,
        "started_at": int(at(-HOUR)),
        "affected_business_ids": [str(world.salon.id)],
    }
    return CreateIncidentCommand(
        user_id=ADMIN, body=CreateIncidentBody.model_validate_json(json.dumps(body))
    )


def test_the_log_is_paged_newest_first() -> None:
    world = IncidentWorld()
    for title in ("Slow replies", "Telegram delays", "Calls dropped"):
        world.use_case.run(outage(world, title))
        world.clock.advance(MINUTE)
    log = ListIncidentsUseCase(AdminsOnly(), IncidentRepository(world.incidents))

    first = log.run(IncidentsQuery(user_id=ADMIN, page=PageRequest(size=PageSize(2))))
    second = log.run(
        IncidentsQuery(
            user_id=ADMIN,
            page=PageRequest(size=PageSize(2), cursor=first.next_cursor),
        )
    )

    assert [str(item.title) for item in first.items] == [
        "Calls dropped",
        "Telegram delays",
    ]
    assert first.next_cursor is not None
    assert [str(item.title) for item in second.items] == ["Slow replies"]
    assert second.next_cursor is None
    assert second.items[0].notice_languages == []


def test_only_platform_admins_read_the_log() -> None:
    world = IncidentWorld()
    log = ListIncidentsUseCase(AdminsOnly(), IncidentRepository(world.incidents))

    with pytest.raises(AccessDeniedError):
        log.run(IncidentsQuery(user_id=UserId(), page=PageRequest()))
