"""
How the owner's checks did, as the cabinet shows them: the failed checks
of an applied version (the "Apply changes" sheet names them) and the
latest "Check now" of a check ("My checks"), with the reason in the
owner's words. Shared by the assistants (apply) and autotests (checks)
packages.
"""

from collections.abc import Mapping, Sequence

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.assistants import AutotestOutcome
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import (
    AutotestRunDocument,
    AutotestScenarioResult,
    AutotestTranscriptLine,
)
from app.schemas.domain.autotest_cases import (
    AutotestCaseDocument,
    OwnerCheckProbe,
    OwnerCheckSnapshot,
)
from app.schemas.dto.assistants.autotest_cases import OwnerCheckOutcomeView
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.assistants.constrained_strings import AutotestCaseQuestion
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.schemas.typings.assistants.strings import OwnerCheckFailureReason
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.setup.owner_check_reasons import (
    CHECK_NOT_PLAYED_REASON,
    EXPECTATION_REASONS,
    fill_expected_text,
)


def describe_failure(
    resolver: LocalizedTextResolverContract,
    snapshot: OwnerCheckSnapshot,
    outcome: AutotestOutcome,
    language: LanguageTag,
) -> OwnerCheckFailureReason | None:
    """Why the check failed in the owner's words; None when it passed."""

    if outcome is AutotestOutcome.PASSED:
        return None

    text: LocalizedText = (
        EXPECTATION_REASONS[snapshot.expectation]
        if outcome is AutotestOutcome.FAILED
        else CHECK_NOT_PLAYED_REASON
    )
    return OwnerCheckFailureReason(
        fill_expected_text(
            str(resolver.resolve(text, language)),
            None if snapshot.expected_text is None else str(snapshot.expected_text),
        )
    )


def first_answer(transcript: Sequence[AutotestTranscriptLine]) -> MessageText | None:
    return next(
        (line.text for line in transcript if line.author is MessageAuthor.ASSISTANT),
        None,
    )


def snapshot_of(
    result: AutotestScenarioResult, case: AutotestCaseDocument | None
) -> OwnerCheckSnapshot | None:
    """
    What the result's check asked: kept with the result, else (a result
    stored before) the check as it is now, else its first question.
    """

    if result.owner_check is not None:
        return result.owner_check

    if case is not None:
        return OwnerCheckSnapshot(
            question=case.question,
            expectation=case.expectation,
            expected_text=case.expected_text,
        )

    return None


def list_failed_owner_checks(
    resolver: LocalizedTextResolverContract,
    run: AutotestRunDocument,
    cases: Mapping[AutotestCaseId, AutotestCaseDocument],
    checked_at: Microseconds,
    language: LanguageTag,
) -> list[OwnerCheckOutcomeView]:
    """The owner's checks the run did not pass, in the order it played them."""

    outcomes: list[OwnerCheckOutcomeView] = []
    for result in run.results:
        if result.autotest_case_id is None or result.outcome is AutotestOutcome.PASSED:
            continue

        snapshot: OwnerCheckSnapshot | None = snapshot_of(
            result, cases.get(result.autotest_case_id)
        )
        if snapshot is None:
            continue

        outcomes.append(
            OwnerCheckOutcomeView(
                autotest_case_id=result.autotest_case_id,
                question=AutotestCaseQuestion(str(snapshot.question)),
                expectation=snapshot.expectation,
                expected_text=snapshot.expected_text,
                outcome=result.outcome,
                check_codes=list(result.check_codes),
                reason=describe_failure(resolver, snapshot, result.outcome, language),
                judge_notes=list(result.judge_notes),
                answer=first_answer(result.transcript),
                conversation_id=result.conversation_id,
                answer_message_id=result.answer_message_id,
                assistant_version_id=run.assistant_version_id,
                checked_at=checked_at,
            )
        )

    return outcomes


def to_probe_view(
    resolver: LocalizedTextResolverContract,
    case: AutotestCaseDocument,
    probe: OwnerCheckProbe,
    language: LanguageTag,
) -> OwnerCheckOutcomeView:
    """A check's "Check now" as the cabinet shows it."""

    snapshot = OwnerCheckSnapshot(
        question=case.question,
        expectation=case.expectation,
        expected_text=case.expected_text,
    )
    return OwnerCheckOutcomeView(
        autotest_case_id=case.id,
        question=case.question,
        expectation=case.expectation,
        expected_text=case.expected_text,
        outcome=probe.outcome,
        check_codes=list(probe.check_codes),
        reason=describe_failure(resolver, snapshot, probe.outcome, language),
        judge_notes=list(probe.judge_notes),
        answer=probe.answer,
        conversation_id=probe.conversation_id,
        answer_message_id=probe.answer_message_id,
        assistant_version_id=probe.assistant_version_id,
        checked_at=probe.checked_at,
    )
