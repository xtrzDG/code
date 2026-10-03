"""Starting a website import: the address check, one at a time, 10 an hour."""

from datetime import timedelta

import pytest

from app.schemas.constants.jobs import JobLane
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.website_import import WebsiteImportStatus
from app.schemas.dto.website_import import (
    GetWebsiteImportQuery,
    WebsiteImportJobPayload,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    RateLimitedError,
    ValidationFailedError,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.knowledge.website_import.start_website_import_use_case import (
    IMPORT_WEBSITE_JOB,
)
from tests.knowledge.knowledge_store import DEFAULT_NOW
from tests.knowledge.website_import.website_import_world import WebsiteImportWorld


def reasons_of(
    error: ValidationFailedError | ConflictError,
) -> list[tuple[str, list[str]]]:
    return [
        (str(reason.code), [str(detail) for detail in reason.details])
        for reason in error.reasons
    ]


def test_an_import_is_queued_for_the_worker() -> None:
    world = WebsiteImportWorld()

    view = world.start_import(user_id=world.staff_id)

    assert view.status is WebsiteImportStatus.QUEUED
    assert str(view.url) == "https://cafe.example"
    assert (int(view.pages_planned), int(view.pages_read)) == (0, 0)
    assert view.result is None
    [job] = world.job_queue.jobs
    assert job.name == IMPORT_WEBSITE_JOB
    assert job.lane is JobLane.DEFAULT
    assert job.business_id == world.business.id
    assert str(job.serial_key) == f"website_import:{world.business.id}"
    payload = WebsiteImportJobPayload.model_validate_json(str(job.payload))
    assert payload.import_id == view.id
    assert world.events.kinds() == [LiveEventKind.KNOWLEDGE_IMPORT_PROGRESS]
    current = world.current().current
    assert current is not None and current.id == view.id
    assert world.website.requested == []


@pytest.mark.parametrize(
    ("url", "detail"),
    [
        ("http://127.0.0.1/", "not_public"),
        ("http://169.254.169.254/latest", "not_public"),
        ("http://[::1]/", "not_public"),
        ("http://localhost:80/", "not_public"),
        ("https://intranet.internal/", "not_public"),
        ("https://cafe.example:8080/", "port_not_allowed"),
        ("https://owner:secret@cafe.example/", "credentials_in_url"),
    ],
)
def test_addresses_that_cannot_be_read_are_refused_at_once(
    url: str, detail: str
) -> None:
    world = WebsiteImportWorld()

    with pytest.raises(ValidationFailedError) as refused:
        world.start_import(url)

    assert reasons_of(refused.value) == [("website_link_invalid", [detail])]
    assert world.job_queue.jobs == []
    assert world.current().current is None


def test_only_one_import_runs_at_a_time() -> None:
    world = WebsiteImportWorld()
    first = world.start_import()

    with pytest.raises(ConflictError) as running:
        world.start_import("https://cafe.example/en")

    assert reasons_of(running.value) == [("website_import_running", [])]
    current = world.current().current
    assert current is not None and current.id == first.id

    # Done: the next import replaces it.
    world.run_queued()
    second = world.start_import("https://cafe.example/en")
    current = world.current().current
    assert current is not None and current.id == second.id != first.id
    assert current.status is WebsiteImportStatus.QUEUED


def test_an_abandoned_import_does_not_block_a_new_one() -> None:
    world = WebsiteImportWorld()
    world.start_import()

    world.clock_source.set(DEFAULT_NOW + timedelta(minutes=16))
    restarted = world.start_import()

    current = world.current().current
    assert current is not None and current.id == restarted.id


def test_ten_imports_an_hour_at_most() -> None:
    world = WebsiteImportWorld()
    for _ in range(10):
        world.start_import()
        world.run_queued()

    with pytest.raises(RateLimitedError) as limited:
        world.start_import()

    assert limited.value.retry_after_seconds is not None
    assert int(limited.value.retry_after_seconds) > 0
    world.clock_source.set(DEFAULT_NOW + timedelta(hours=2))
    assert world.start_import().status is WebsiteImportStatus.QUEUED


def test_only_members_of_the_business_may_import() -> None:
    world = WebsiteImportWorld()

    with pytest.raises(NotFoundError):
        world.start_import(user_id=UserId())

    with pytest.raises(NotFoundError):
        world.get.run(
            GetWebsiteImportQuery(user_id=UserId(), business_id=world.business.id)
        )
