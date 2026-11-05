"""
How "Check now" is kept: on the check, in one step, only while the check
is still asked as it was when the probe started (the answer belongs to
that question); the owner hears the outcome either way. And a new check
whose question tells too little about its language takes the business's.
"""

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.autotest_case_repository import AutotestCaseRepository
from app.schemas.constants.assistants import (
    AutotestCheckCode,
    AutotestExpectation,
    AutotestOutcome,
    AutotestScenarioKind,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.assistants import AutotestScenarioResult, AutotestTranscriptLine
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.dto.assistants.autotest_cases import (
    OwnerCheckProbeOutcome,
    OwnerCheckProbeStart,
)
from app.schemas.typings.assistants.constrained_strings import (
    AutotestCaseQuestion,
    AutotestExpectedText,
)
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.autotests.cases.record_owner_check_probe_use_case import (
    RecordOwnerCheckProbeUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.assembly.scenario_check_builders import scenario_run
from tests.live_events.recording_event_publisher import RecordingEventPublisher
from tests.teaching.teaching_world import build_teaching_world
from tests.teaching.test_autotest_cases import create

NOW_NS: int = 1_790_000_000_000_000_000
ANSWER: str = "Я тестовый помощник."


def recorder(
    cases: AutotestCaseRepository, events: RecordingEventPublisher
) -> RecordOwnerCheckProbeUseCase:
    return RecordOwnerCheckProbeUseCase(
        autotest_case_repo=cases,
        localized_text_resolver=LocalizedTextResolver(),
        live_events=events,
        wall_clock=WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: NOW_NS,
        ),
    )


def played(case: AutotestCaseDocument) -> OwnerCheckProbeOutcome:
    """The check asked of a version, failed: the answer misses its words."""

    run = scenario_run(AutotestScenarioKind.OWNER_CHECK)
    return OwnerCheckProbeOutcome(
        start=OwnerCheckProbeStart(
            case=case, scenario_run=run, language=LanguageTag("ru")
        ),
        result=AutotestScenarioResult(
            scenario_key=run.scenario.key,
            kind=AutotestScenarioKind.OWNER_CHECK,
            language=LanguageTag("ru"),
            outcome=AutotestOutcome.FAILED,
            check_codes=[AutotestCheckCode.EXPECTED_TEXT_MISSING],
            transcript=[
                AutotestTranscriptLine(
                    author=MessageAuthor.CUSTOMER, text=MessageText(str(case.question))
                ),
                AutotestTranscriptLine(
                    author=MessageAuthor.ASSISTANT, text=MessageText(ANSWER)
                ),
            ],
            cost_micro_usd=CostMicroUsd(0),
        ),
    )


def stored_case(cases: AutotestCaseRepository) -> AutotestCaseDocument:
    case = AutotestCaseDocument(
        business_id=scenario_run(AutotestScenarioKind.OWNER_CHECK).business.id,
        question=AutotestCaseQuestion("Есть парковка?"),
        expectation=AutotestExpectation.MUST_MENTION,
        expected_text=AutotestExpectedText("во дворе"),
        language=LanguageTag("ru"),
        updated_at=Microseconds(10),
    )
    cases.save(case)
    return case


def test_a_probe_is_kept_on_the_unchanged_check() -> None:
    cases = AutotestCaseRepository(
        InMemoryDocumentCollectionAdapter(AutotestCaseDocument)
    )
    events = RecordingEventPublisher()
    case = stored_case(cases)

    view = recorder(cases, events).run(played(case))

    kept = cases.get(case.business_id, case.id)
    assert kept is not None and kept.last_probe is not None
    assert kept.last_probe.outcome is AutotestOutcome.FAILED
    assert str(kept.last_probe.answer) == ANSWER
    assert view.reason == "Ответ должен упомянуть «во дворе», а не упомянул."
    assert events.kinds() == [LiveEventKind.ASSISTANT_APPLY]


def test_a_probe_of_a_check_changed_meanwhile_is_told_but_not_kept() -> None:
    cases = AutotestCaseRepository(
        InMemoryDocumentCollectionAdapter(AutotestCaseDocument)
    )
    events = RecordingEventPublisher()
    case = stored_case(cases)
    # The owner rewrote the check while the probe was talking.
    cases.save(
        case.model_copy(
            update={
                "question": AutotestCaseQuestion("Где парковаться?"),
                "updated_at": Microseconds(20),
            }
        )
    )

    view = recorder(cases, events).run(played(case))

    kept = cases.get(case.business_id, case.id)
    assert kept is not None
    assert kept.last_probe is None
    assert str(kept.question) == "Где парковаться?"
    assert view.outcome is AutotestOutcome.FAILED
    assert str(view.question) == "Есть парковка?"
    assert events.kinds() == []


def test_a_question_that_tells_too_little_takes_the_business_language() -> None:
    world = build_teaching_world()

    numbers = create(world, question="22?", expectation="must_hand_off")
    english = create(
        world, question="Can I bring my dog to dinner?", expectation="must_hand_off"
    )

    assert world.brain.business.default_language == "ka"
    assert numbers.language == "ka"
    assert english.language == "en"
