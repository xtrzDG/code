"""
An incident of every business: recording it stores the incident and its
`expand_incident` job in one transaction; the worker then walks the
businesses a keyset batch at a time, each batch's audit entries and owner
notices with the incident's cursor, until the last batch ends the walk.
"""

import pytest

from app.schemas.constants.incidents import IncidentScope
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.incidents import CreateIncidentCommand
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.use_cases.admin.incidents.incident_expansion import (
    EXPAND_INCIDENT_JOB,
    expansion_payload,
)
from app.use_cases.admin.incidents.incident_views import incident_view
from tests.platform_ops.incident_world import IncidentWorld, breach
from tests.platform_ops.ops_documents import business, member
from tests.platform_ops.ops_world import put

BATCH: int = 2


def every_business(**changes: object) -> CreateIncidentCommand:
    return breach(scope="all_businesses", **changes)


def with_more_businesses(world: IncidentWorld, count: int) -> list[BusinessDocument]:
    """`count` more businesses, each with one English-speaking owner."""

    added: list[BusinessDocument] = []
    for index in range(count):
        owner = UserDocument(
            login_method=LoginMethod.EMAIL,
            email=EmailAddress(f"owner{index}@shop.example"),
            locale=LanguageTag("en"),
        )
        put(world.users, owner)
        shop = business(f"Shop {index}", member(owner.id, BusinessMemberRole.OWNER))
        put(world.businesses, shop)
        added.append(shop)
    return added


def run_next_job(world: IncidentWorld, batch_size: int = BATCH) -> JobReport:
    queued = world.queue.jobs.pop(0)
    assert queued.name == EXPAND_INCIDENT_JOB
    return world.expansion(batch_size).run(
        QueuedJobInput(
            job_id=queued.job_id, job_name=queued.name, payload=queued.payload
        )
    )


def test_recording_it_stores_the_incident_and_its_walk_together() -> None:
    world = IncidentWorld()

    view = world.use_case.run(every_business())

    assert view.scope is IncidentScope.ALL_BUSINESSES
    assert view.is_expanding and int(view.affected_business_count) == 0
    assert view.affected_business_ids == []
    [job] = world.queue.jobs
    assert job.name == EXPAND_INCIDENT_JOB and job.lane is JobLane.DEFAULT
    assert str(job.serial_key) == f"incident:{view.id}"
    assert world.transactions.outcomes == ["commit"]
    assert world.notifier.sent == [] and world.audit.list_all() == []


def test_an_all_businesses_breach_notifies_in_batches() -> None:
    world = IncidentWorld()
    with_more_businesses(world, 3)
    view = world.use_case.run(every_business())

    processed: list[int] = []
    notices_per_run: list[int] = []
    while world.queue.jobs:
        before = len(world.notifier.sent)
        processed.append(int(run_next_job(world).processed_count))
        notices_per_run.append(len(world.notifier.sent) - before)

    # Salon (two owners) and Café; Shops 0 and 1; Shop 2 ends the walk.
    assert processed == [2, 2, 1]
    assert notices_per_run == [3, 2, 1]
    assert world.transactions.outcomes == ["commit"] * 4
    [stored] = world.incidents.list_all()
    assert stored.expanded_at is not None
    assert int(stored.reached_business_count or 0) == 5
    assert int(stored.notified_owner_count) == 6 and stored.notified_at is not None
    finished = incident_view(stored)
    assert not finished.is_expanding and int(finished.affected_business_count) == 5
    entries = world.audit.list_all()
    assert len(entries) == 5
    assert {str(entry.entity_id) for entry in entries} == {str(view.id)}
    assert len({entry.business_id for entry in entries}) == 5


def test_without_a_unit_of_work_it_is_recorded_and_walked_all_the_same() -> None:
    # In-memory storage (the demo and the in-memory API) has no unit of work.
    world = IncidentWorld(transactional=False)

    world.use_case.run(every_business(kind="outage", notice_texts=[]))
    while world.queue.jobs:
        run_next_job(world)

    [stored] = world.incidents.list_all()
    assert stored.expanded_at is not None
    assert int(stored.reached_business_count or 0) == 2
    assert world.transactions.outcomes == []


def test_a_repeated_run_resumes_at_the_cursor_and_ends_quietly() -> None:
    world = IncidentWorld()
    with_more_businesses(world, 1)
    world.use_case.run(every_business())
    queued = world.queue.jobs[0]
    job = QueuedJobInput(
        job_id=queued.job_id, job_name=queued.name, payload=queued.payload
    )

    # The same job delivered three times: each run takes the next batch.
    reports = [world.expansion(BATCH).run(job) for _ in range(3)]

    assert [int(report.processed_count) for report in reports] == [2, 1, 0]
    assert len(world.audit.list_all()) == 3
    assert len(world.notifier.sent) == 4


def test_a_business_created_during_the_walk_is_reached_at_its_end() -> None:
    world = IncidentWorld()
    world.use_case.run(every_business(kind="outage", notice_texts=[]))
    run_next_job(world)

    [late] = with_more_businesses(world, 1)
    while world.queue.jobs:
        run_next_job(world)

    assert late.id in {entry.business_id for entry in world.audit.list_all()}
    [stored] = world.incidents.list_all()
    assert int(stored.reached_business_count or 0) == 3
    assert world.notifier.sent == []


def test_a_walk_of_exactly_full_batches_ends_with_an_empty_one() -> None:
    world = IncidentWorld()
    world.use_case.run(every_business(kind="outage", notice_texts=[]))

    first = run_next_job(world)
    last = run_next_job(world)

    assert int(first.processed_count) == 2 and int(last.processed_count) == 0
    assert world.queue.jobs == []
    [stored] = world.incidents.list_all()
    assert stored.expanded_at is not None


def test_a_listed_incident_is_not_walked() -> None:
    world = IncidentWorld()
    view = world.use_case.run(breach(world.salon))

    report = world.expansion(BATCH).run(
        QueuedJobInput(
            job_id=QueuedJobId(),
            job_name=EXPAND_INCIDENT_JOB,
            payload=expansion_payload(view.id),
        )
    )

    assert int(report.processed_count) == 0
    assert world.queue.jobs == []
    assert int(view.affected_business_count) == 1 and not view.is_expanding


@pytest.mark.parametrize(
    "changes",
    [
        {"scope": "all_businesses", "affected_business_ids": ["named"]},
        {"scope": "listed", "affected_business_ids": []},
    ],
)
def test_the_scope_and_the_named_businesses_agree(changes: dict[str, object]) -> None:
    world = IncidentWorld()
    named = [str(world.salon.id)] if changes["affected_business_ids"] else []

    with pytest.raises(ValueError, match="business"):
        breach(**{**changes, "affected_business_ids": named})
