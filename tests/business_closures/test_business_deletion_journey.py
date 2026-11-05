"""
An owner closes the demo restaurant: 30 days pending deletion (the
assistant paused, the channels off), then the deletion job removes every
row and file of it, keeps only what the law keeps, records a deletion
certificate and the platform's audit entry, and leaves the stranger's
business exactly as it was.
"""

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.audit_trail import PlatformAuditFilter
from app.schemas.dto.job_queue import QueuedJobPageQuery
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.platform.constrained_integers import (
    KeysetReadLimit,
    PageSize,
)
from app.utilities.business_closures.retained_tables import RETAINED_TABLES
from app.utilities.privacy.processor_erasure_jobs import ERASE_PROCESSOR_COPIES_JOB
from tests.business_closures.closure_world import (
    DAY_SECONDS,
    STRANGER_OWNER_PHONE,
    ClosureWorld,
    open_closure_world,
)
from tests.e2e.harness import bearer

THIRTY_DAYS_MICROSECONDS: int = 30 * DAY_SECONDS * 1_000_000


def channel_statuses(world: ClosureWorld) -> dict[str, str]:
    channels = world.workshop.client.get(
        f"/v1/businesses/{world.business_b}/channels", headers=world.owner_b
    )
    assert channels.status_code == 200, channels.text
    return {item["channel"]: item["status"] for item in channels.json()}


def business_status(world: ClosureWorld) -> str:
    business = world.workshop.client.get(
        f"/v1/businesses/{world.business_b}", headers=world.owner_b
    )
    assert business.status_code == 200, business.text
    return str(business.json()["status"])


def test_a_closed_business_is_paused_and_counts_down_thirty_days() -> None:
    with open_closure_world() as world:
        assert business_status(world) == "live"
        assert "connected" in channel_statuses(world).values()

        view = world.close_b()

        assert view["state"] == "pending_deletion"
        assert view["reason"] == "owner_request"
        assert view["can_cancel"] is True
        assert view["delete_after"] == int(world.now()) + THIRTY_DAYS_MICROSECONDS
        assert business_status(world) == "paused"
        assert "connected" not in channel_statuses(world).values()
        staff_view = world.workshop.client.get(
            world.closure_path, headers=world.staff_b
        )
        assert staff_view.json()["state"] == "pending_deletion"
        assert staff_view.json()["can_cancel"] is False
        assert staff_view.json()["viewer_is_owner"] is False
        resumed = world.workshop.client.patch(
            f"/v1/businesses/{world.business_b}",
            json={"status": "live"},
            headers=world.owner_b,
        )
        assert resumed.status_code == 409, resumed.text


def test_nothing_is_deleted_before_the_thirty_days_are_over() -> None:
    with open_closure_world() as world:
        world.close_b()
        rows = world.rows_of(world.business_b)
        world.workshop.clock.advance(29 * DAY_SECONDS)

        world.tick("queue_business_deletions")
        world.workshop.run_queued_jobs()

        assert world.rows_of(world.business_b)["businesses"] == 1
        assert world.rows_of(world.business_b)["contacts"] == rows["contacts"]


def test_the_deletion_leaves_nothing_of_the_business_but_what_the_law_keeps() -> None:
    with open_closure_world() as world:
        before_b = world.rows_of(world.business_b)
        before_a = world.rows_of(world.business_a)
        assert before_b["messages"] > 0 and before_b["contacts"] > 0

        world.delete_b_after_thirty_days()

        left = world.rows_of(world.business_b)
        assert set(left) - set(RETAINED_TABLES) <= {"queued_jobs"}
        # What waits in the queue is the deletion's own work: the copies at
        # the sub-processors, erased by their jobs.
        assert left.get("queued_jobs", 0) == len(processor_erasure_jobs(world))
        assert world.rows_of(world.business_a) == before_a


def test_the_owner_downloads_the_deletion_certificate() -> None:
    with open_closure_world() as world:
        world.delete_b_after_thirty_days()
        owner = world.sign_in_owner_b()

        listed = world.workshop.client.get("/v1/me/business-deletions", headers=owner)

        assert listed.status_code == 200, listed.text
        [entry] = [
            item
            for item in listed.json()["items"]
            if item["business_name"] == "Mtsvane Ezo"
        ]
        assert entry["state"] == "completed"
        certificate = world.workshop.client.get(
            f"/v1/me/business-deletions/{entry['id']}/certificate?language=en",
            headers=owner,
        )
        assert certificate.status_code == 200
        assert certificate.headers["content-type"] == "application/pdf"
        assert certificate.content.startswith(b"%PDF")
        stranger = world.workshop.client.get(
            f"/v1/me/business-deletions/{entry['id']}/certificate",
            headers=bearer(world.workshop.sign_in_with_phone(STRANGER_OWNER_PHONE)[0]),
        )
        assert stranger.status_code == 404


def test_the_platform_audit_chain_records_the_deletion_with_its_counts() -> None:
    with open_closure_world() as world:
        world.delete_b_after_thirty_days()

        container = world.workshop.container
        with container.utilities.storage_scope().platform_wide():
            entries = (
                container.repositories.audit_activity_repo().page_platform_entries(
                    KeysetSlice(limit=KeysetReadLimit(50)),
                    PlatformAuditFilter(action=AuditAction.DELETE),
                )
            )

        [deletion] = [
            entry
            for entry in entries
            if str(entry.entity) == "business"
            and str(entry.entity_id) == world.business_b
        ]
        assert deletion.business_id is None
        assert deletion.record_count is not None and int(deletion.record_count) > 100


def processor_erasure_jobs(world: ClosureWorld) -> list[QueuedJobDocument]:
    with world.workshop.container.utilities.storage_scope().platform_wide():
        jobs = world.workshop.container.repositories.queued_job_repo().list_page(
            QueuedJobPageQuery(name=ERASE_PROCESSOR_COPIES_JOB, page_size=PageSize(100))
        )
    return [job for job in jobs if str(job.business_id) == world.business_b]
