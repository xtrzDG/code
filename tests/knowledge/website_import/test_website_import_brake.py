"""A website import while a platform brake holds: refused, or read by no model."""

import pytest

from app.schemas.constants.spend import PlatformBrake
from app.schemas.constants.website_import import (
    WebsiteImportProblem,
    WebsiteImportStatus,
)
from app.schemas.dto.website_import import WebsiteImportView
from app.schemas.exceptions.application_errors import ConflictError
from tests.knowledge.website_import.website_import_world import WebsiteImportWorld


def current_view(world: WebsiteImportWorld) -> WebsiteImportView:
    view: WebsiteImportView | None = world.current().current
    assert view is not None
    return view


@pytest.mark.parametrize("brake", list(PlatformBrake))
def test_an_owner_starts_no_import_while_a_brake_holds(brake: PlatformBrake) -> None:
    world = WebsiteImportWorld()
    world.platform_brakes.brake = brake

    with pytest.raises(ConflictError) as refusal:
        world.start_import()

    [reason] = refusal.value.reasons
    assert (str(reason.code), [str(detail) for detail in reason.details]) == (
        "platform_brake",
        [brake.value],
    )
    assert world.job_queue.jobs == []
    assert world.current().current is None
    world.platform_brakes.brake = None
    assert world.start_import().status is WebsiteImportStatus.QUEUED


def test_an_import_queued_before_the_brake_reads_no_page() -> None:
    world = WebsiteImportWorld()
    world.start_import()
    world.platform_brakes.brake = PlatformBrake.BUDGET_STOP

    report = world.run_queued()

    view = current_view(world)
    assert int(report.processed_count) == 0
    assert (view.status, view.problem, str(view.problem_detail)) == (
        WebsiteImportStatus.FAILED,
        WebsiteImportProblem.READER_UNAVAILABLE,
        "platform_brake",
    )
    assert world.llm.requests == []
