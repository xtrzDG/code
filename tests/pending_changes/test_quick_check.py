"""
"Apply changes" after the first go-live: a quick check of what changed
(the scenarios the changes touch and three core ones, a price question
for each changed price) instead of the whole suite; it publishes on its
own when it passes, keeps the live version when it fails, and discards
the drafts the newer version leaves behind.
"""

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.setup import (
    ApplyAttentionCode,
    ApplyChangesStage,
    PendingChangeArea,
    PendingChangeDetail,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.assistants.assistant_commands import AssistantVersionsQuery
from app.schemas.dto.setup.apply_changes import ApplyChangesView
from app.schemas.dto.setup.pending_changes import PendingChange, PendingChangesRequest
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.assembly.international_business_seeds import seed_italian_restaurant
from tests.assembly.testbed import AssemblyTestbed
from tests.setup.apply_testbed import apply, assert_needs_attention, progress, settle

FAILING_SCORES: dict[str, int] = {
    "facts_and_prices": 1,
    "booking_data": 1,
    "ai_disclosure": 1,
    "handoff": 1,
    "language": 1,
}


def go_live(
    testbed: AssemblyTestbed, business: BusinessDocument
) -> tuple[ApplyChangesView, ApplyChangesView]:
    """The owner applies, the worker runs the checks: the apply started, then live."""

    started = apply(testbed, business)
    testbed.run_worker()
    view = progress(testbed, business)
    assert view.stage is ApplyChangesStage.LIVE, view
    return started, view


def raise_price(
    testbed: AssemblyTestbed, business: BusinessDocument
) -> KnowledgeItemDocument:
    """The owner raises the price of the pizza by one euro."""

    testbed.advance(60)
    item = next(
        item
        for item in testbed.knowledge_repo.list_by_business(business.id)
        if str(item.title) == "Pizza Margherita"
    )
    assert item.price_minor is not None
    item.price_minor = MoneyAmountMinor(int(item.price_minor) + 100)
    item.updated_at = testbed.wall_clock.now_unix()
    testbed.knowledge_repo.save(item)
    return item


def planned_keys(
    testbed: AssemblyTestbed, business: BusinessDocument, version_id: AssistantVersionId
) -> list[str]:
    version = testbed.version(business.id, version_id)
    assert version.autotest_run_id is not None
    run = testbed.run_repo.get(business.id, version.autotest_run_id)
    assert run is not None
    return sorted(str(result.scenario_key) for result in run.results)


def pending(
    testbed: AssemblyTestbed, business: BusinessDocument
) -> list[PendingChange]:
    current = testbed.business(business.id)
    assert current.published_assistant_version_id is not None
    return testbed.collect_pending_changes_use_case.run(
        PendingChangesRequest(
            business=current,
            version=testbed.version(
                business.id, current.published_assistant_version_id
            ),
            language=LanguageTag("en"),
        )
    )


def test_a_new_price_is_checked_quickly_and_published_on_its_own() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    first, _ = go_live(testbed, business)
    assert first.checks_total is not None and int(first.checks_total) > 10

    raise_price(testbed, business)
    changes = pending(testbed, business)
    assert [(change.area, change.detail) for change in changes] == [
        (PendingChangeArea.OFFER, PendingChangeDetail.PRICE)
    ]
    assert changes[0].before == "8.50 EUR" and changes[0].after == "9.50 EUR"

    started = apply(testbed, business)
    assert started.stage is ApplyChangesStage.CHECKING
    assert started.checks_total == 4
    testbed.run_worker()
    second = progress(testbed, business)

    assert second.stage is ApplyChangesStage.LIVE
    assert second.version_number == 2
    assert second.assistant_version_id is not None
    assert (
        testbed.business(business.id).published_assistant_version_id
        == second.assistant_version_id
    )
    # Three core scenarios in Italian and the new price, asked in Italian.
    assert planned_keys(testbed, business, second.assistant_version_id) == [
        "booking__it",
        "human_request__it",
        "price_question__it",
        "price_question__it__1",
    ]
    assert pending(testbed, business) == []


def test_a_failed_quick_check_keeps_the_live_version_and_names_the_check() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    _, first = go_live(testbed, business)
    raise_price(testbed, business)
    testbed.judge_scores["price_question__it__1"] = FAILING_SCORES

    apply(testbed, business)
    testbed.run_worker()
    view = progress(testbed, business)

    assert_needs_attention(view, ApplyAttentionCode.CHECKS_FAILED)
    assert view.attention[0].details == ["price_question"]
    assert view.assistant_version_id is not None
    assert view.assistant_version_id != first.assistant_version_id
    assert (
        testbed.business(business.id).published_assistant_version_id
        == first.assistant_version_id
    )
    assert testbed.version(business.id, view.assistant_version_id).status is (
        AssistantVersionStatus.TESTS_FAILED
    )
    assert len(pending(testbed, business)) == 1


def test_drafts_left_behind_are_discarded_once_a_newer_version_goes_live() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    _, first = go_live(testbed, business)
    raise_price(testbed, business)
    testbed.judge_scores["price_question__it__1"] = FAILING_SCORES
    apply(testbed, business)
    testbed.run_worker()
    failed = progress(testbed, business).assistant_version_id
    assert failed is not None
    draft = testbed.assemble(business.id, run_autotests=False)

    del testbed.judge_scores["price_question__it__1"]
    testbed.advance(60)
    _, live = go_live(testbed, business)

    assert live.assistant_version_id not in (
        failed,
        draft.id,
        first.assistant_version_id,
    )
    for left_behind in (failed, draft.id):
        assert testbed.version(business.id, left_behind).discarded_at is not None
    assert first.assistant_version_id is not None
    assert testbed.version(business.id, first.assistant_version_id).status is (
        AssistantVersionStatus.ARCHIVED
    )
    listed = testbed.list_versions_use_case.run(
        AssistantVersionsQuery(user_id=testbed.owner_id, business_id=business.id)
    )
    assert {str(version.id) for version in listed} == {
        str(first.assistant_version_id),
        str(live.assistant_version_id),
    }


def test_every_step_of_the_apply_is_announced_to_open_cabinets() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))

    _, live = go_live(testbed, business)

    stored = testbed.apply_repo.get_by_business(business.id)
    assert stored is not None
    events = testbed.apply_events.events
    assert {published.event for published in events} == {LiveEventKind.ASSISTANT_APPLY}
    # Started, checking, publishing, live: the apply and its version.
    assert len(events) >= 3
    assert {published.ids[0] for published in events} == {str(stored.id)}
    assert events[-1].ids == (str(stored.id), str(live.assistant_version_id))
