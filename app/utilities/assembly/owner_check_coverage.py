"""
Which of the owner's checks a version was not checked against yet: the
pending "owner checks" of "Apply changes".

A version is checked against a check when its latest autotest run played
the check after the check's last change, or when "Check now" asked the
check of that very version after its last change and it passed. A paused
check is not played, so it is never pending.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestOutcome
from app.schemas.constants.setup import PendingChangeAction, PendingChangeArea
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.autotest_cases import AutotestCaseDocument, OwnerCheckProbe
from app.schemas.dto.setup.pending_changes import (
    PendingChange,
    PendingOwnerCheckView,
)
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId, AutotestRunId
from app.schemas.typings.setup.strings import PendingChangeSubject


def find_reference_run_id(version: AssistantVersionDocument) -> AutotestRunId | None:
    """The run the version was last judged by (its verdict), else its last run."""

    if version.autotest_verdict is not None:
        return version.autotest_verdict.run_id

    return version.autotest_run_id


def is_probed_against(
    case: AutotestCaseDocument, version: AssistantVersionDocument
) -> bool:
    """Whether "Check now" passed on `version` after the check's last change."""

    probe: OwnerCheckProbe | None = case.last_probe
    return (
        probe is not None
        and probe.assistant_version_id == version.id
        and probe.outcome is AutotestOutcome.PASSED
        and int(probe.checked_at) >= int(case.updated_at)
    )


def collect_owner_check_changes(
    cases: Sequence[AutotestCaseDocument],
    version: AssistantVersionDocument,
    run: AutotestRunDocument | None,
) -> list[PendingChange]:
    """
    One OWNER_CHECKS change per active check `version` was not checked
    against (in the order they were written): ADDED when its run never
    played the check, CHANGED when the check changed after the run.
    """

    played: set[AutotestCaseId] = (
        set()
        if run is None
        else {
            result.autotest_case_id
            for result in run.results
            if result.autotest_case_id is not None
        }
    )
    changes: list[PendingChange] = []
    for case in cases:
        if not case.is_active or is_probed_against(case, version):
            continue

        was_played: bool = case.id in played
        if (
            was_played
            and run is not None
            and int(case.updated_at) <= int(run.created_at)
        ):
            continue

        changes.append(
            PendingChange(
                area=PendingChangeArea.OWNER_CHECKS,
                action=(
                    PendingChangeAction.CHANGED
                    if was_played
                    else PendingChangeAction.ADDED
                ),
                subject=PendingChangeSubject(str(case.question)),
                autotest_case_id=case.id,
            )
        )

    return changes


def is_owner_check_change(change: PendingChange) -> bool:
    return change.area is PendingChangeArea.OWNER_CHECKS


def describe_owner_check_changes(
    changes: Sequence[PendingChange], cases: Sequence[AutotestCaseDocument]
) -> list[PendingOwnerCheckView]:
    """
    The OWNER_CHECKS changes with what each check asks, in their order; a
    check removed since the changes were collected is left out.
    """

    by_id: dict[AutotestCaseId, AutotestCaseDocument] = {
        case.id: case for case in cases
    }
    views: list[PendingOwnerCheckView] = []
    for change in changes:
        case: AutotestCaseDocument | None = (
            None
            if change.autotest_case_id is None
            else by_id.get(change.autotest_case_id)
        )
        if not is_owner_check_change(change) or case is None:
            continue

        views.append(
            PendingOwnerCheckView(
                autotest_case_id=case.id,
                action=change.action,
                question=case.question,
                expectation=case.expectation,
                expected_text=case.expected_text,
                language=case.language,
            )
        )

    return views
