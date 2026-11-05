"""The milestones job notices live businesses' first customers without the cabinet."""

from app.schemas.dto.jobs import JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName
from tests.e2e.harness import Workshop
from tests.setup.launch_steps import create_assistant
from tests.setup.test_activation_milestones import (
    milestones,
    open_with_website_chat,
    write_from_the_website,
)


def run_job(workshop: Workshop) -> int:
    job = workshop.container.use_cases.guide.notice_milestones_use_case()
    tick = JobTick(
        job_name=JobName("notice_milestones"),
        scheduled_at=workshop.container.time_provider.microsecond_wall_clock().now_unix(),
    )
    with workshop.container.utilities.storage_scope().platform_wide():
        return int(job.run(tick).processed_count)


def test_the_job_records_milestones_of_live_businesses_only(workshop: Workshop) -> None:
    create_assistant(workshop, phone="+995599000111")
    assistant = open_with_website_chat(workshop)
    workshop.clock.advance(600)
    write_from_the_website(workshop, assistant, "Здравствуйте")

    # One live business is checked; the one still in its setup is not.
    assert run_job(workshop) == 1
    repo = workshop.container.repositories.activation_event_repo()
    with workshop.container.utilities.storage_scope().platform_wide():
        stored = repo.list_by_business(BusinessId(assistant.business_id))
    assert "first_conversation" in {event.kind.value for event in stored}
    assert "first_conversation" in milestones(workshop, assistant)
