"""When a website cannot be read: refused at the worker, unreachable, no reader."""

import pytest

from app.schemas.constants.website_import import (
    WebsiteImportProblem,
    WebsiteImportStatus,
)
from app.schemas.domain.website_imports import WebsiteImportDocument
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.dto.website_import import WebsiteImportView
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.conversations.strings import MessageText
from tests.knowledge.website_import.site_fixtures import SITE
from tests.knowledge.website_import.website_import_world import WebsiteImportWorld
from tests.web_fetching.fetch_fakes import http_response, page, redirect


def current_view(world: WebsiteImportWorld) -> WebsiteImportView:
    view: WebsiteImportView | None = world.current().current
    assert view is not None
    return view


def failure_of(view: WebsiteImportView) -> tuple[WebsiteImportStatus, str, str]:
    return (
        view.status,
        "" if view.problem is None else view.problem.value,
        "" if view.problem_detail is None else str(view.problem_detail),
    )


def test_a_host_that_resolves_privately_is_refused_by_the_worker() -> None:
    world = WebsiteImportWorld()
    world.website.add_host("rebind.example", ["10.0.0.5"])
    world.start_import("https://rebind.example")

    world.run_queued()

    assert failure_of(current_view(world)) == (
        WebsiteImportStatus.FAILED,
        WebsiteImportProblem.INVALID.value,
        "not_public",
    )
    assert world.llm.requests == []


@pytest.mark.parametrize(
    ("home", "problem", "detail"),
    [
        (http_response(503), WebsiteImportProblem.UNREACHABLE, "http_status:503"),
        (
            redirect("http://169.254.169.254/latest/meta-data"),
            WebsiteImportProblem.INVALID,
            "not_public",
        ),
        (
            http_response(200, {"Content-Type": "application/pdf"}, b"%PDF"),
            WebsiteImportProblem.UNREADABLE,
            "media_type:application/pdf",
        ),
    ],
)
def test_a_start_page_that_cannot_be_read_fails_the_import(
    home: list[bytes], problem: WebsiteImportProblem, detail: str
) -> None:
    world = WebsiteImportWorld()
    world.website.pages[f"{SITE}/"] = home
    world.start_import()

    world.run_queued()

    view = current_view(world)
    assert failure_of(view) == (WebsiteImportStatus.FAILED, problem.value, detail)
    assert view.finished_at is not None
    assert view.result is None
    assert world.llm.requests == []


def test_an_unknown_host_is_unreachable() -> None:
    world = WebsiteImportWorld()
    world.start_import("https://nowhere.example")

    world.run_queued()

    assert failure_of(current_view(world)) == (
        WebsiteImportStatus.FAILED,
        WebsiteImportProblem.UNREACHABLE.value,
        "unknown_host",
    )


def test_no_page_read_by_the_model_means_the_reader_is_unavailable() -> None:
    world = WebsiteImportWorld()
    world.respond = lambda request: ScriptedLlmTurn(
        text=MessageText("Sorry, I cannot help with that.")
    )
    world.start_import()

    world.run_queued()

    view = current_view(world)
    assert failure_of(view) == (
        WebsiteImportStatus.FAILED,
        WebsiteImportProblem.READER_UNAVAILABLE.value,
        "reader_failed",
    )
    assert int(view.pages_skipped) == 7
    # The unreadable answers still cost tokens.
    stored = world.website_import_repo.get_by_business(world.business.id)
    assert stored is not None and int(stored.cost_micro_usd) > 0


def test_a_provider_outage_on_one_page_skips_only_that_page() -> None:
    world = WebsiteImportWorld()
    answer = world.respond

    def flaky(request: LlmRequest) -> ScriptedLlmTurn:
        if "/faq" in str(request.transcript[0]):
            raise ExternalServiceError("The model is unavailable.")

        return answer(request)

    world.respond = flaky
    world.start_import()

    world.run_queued()

    view = current_view(world)
    assert view.status is WebsiteImportStatus.DONE
    assert (int(view.pages_read), int(view.pages_skipped)) == (4, 3)
    assert view.result is not None
    titles = [str(entry.item.title) for entry in view.result.items]
    assert "Do you have parking?" not in titles


def test_an_empty_page_is_skipped_without_asking_the_model() -> None:
    world = WebsiteImportWorld()
    world.website.pages[f"{SITE}/faq"] = page("<script>only code</script>")
    world.start_import()

    world.run_queued()

    view = current_view(world)
    assert view.status is WebsiteImportStatus.DONE
    assert len(world.llm.requests) == 4


def test_a_replaced_or_finished_import_job_does_nothing() -> None:
    world = WebsiteImportWorld()
    world.start_import()
    world.run_queued()
    requests_after_first: int = len(world.website.requested)

    report = world.run_queued()

    assert int(report.processed_count) == 0
    assert len(world.website.requested) == requests_after_first


def test_a_rerun_of_an_interrupted_import_starts_over() -> None:
    world = WebsiteImportWorld()
    world.start_import()
    world.run_queued()
    stored = world.website_import_repo.get_by_business(world.business.id)
    assert stored is not None

    def reopen(current: WebsiteImportDocument) -> bool:
        current.status = WebsiteImportStatus.READING
        current.finished_at = None
        return True

    world.website_import_repo.change(world.business.id, stored.import_id, reopen)

    world.run_queued()

    view = current_view(world)
    assert view.status is WebsiteImportStatus.DONE
    assert view.result is not None
    # The drafts of the interrupted run were discarded, not doubled.
    assert len(view.result.items) == 4
    assert len(world.knowledge_item_repo.list_by_business(world.business.id)) == 4


def test_the_last_attempt_of_a_crashing_job_marks_the_import_interrupted() -> None:
    world = WebsiteImportWorld()

    def crash(request: LlmRequest) -> ScriptedLlmTurn:
        raise RuntimeError("bug")

    world.respond = crash
    world.start_import()

    with pytest.raises(RuntimeError):
        world.run_queued()
    assert current_view(world).status is WebsiteImportStatus.READING

    with pytest.raises(RuntimeError):
        world.run_queued(is_final_attempt=True)
    assert failure_of(current_view(world)) == (
        WebsiteImportStatus.FAILED,
        WebsiteImportProblem.INTERRUPTED.value,
        "worker_failed",
    )
