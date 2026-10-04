"""The owner's checks as "My checks" shows them, with their latest result."""

from typed_time_provider import Microseconds

from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
    AutotestScenarioResult,
    AutotestVerdict,
)
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.dto.assistants.autotest_cases import (
    AutotestCaseResultView,
    AutotestCaseView,
)
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText


def to_case_view(
    case: AutotestCaseDocument, result: AutotestCaseResultView | None = None
) -> AutotestCaseView:
    return AutotestCaseView(
        id=case.id,
        question=case.question,
        expectation=case.expectation,
        expected_text=case.expected_text,
        language=case.language,
        source=case.source,
        source_conversation_id=case.source_conversation_id,
        is_active=case.is_active,
        created_at=case.created_at,
        last_result=result,
    )


def latest_case_results(
    assistant_version_repo: AssistantVersionRepoContract,
    autotest_run_repo: AutotestRunRepoContract,
    business_id: BusinessId,
) -> dict[AutotestCaseId, AutotestCaseResultView]:
    """
    The results of the checks in the latest finished run of the business
    (the version whose verdict is the newest): one read of the versions,
    a business keeps a handful, and one of the run.
    """

    verdicts: list[tuple[AutotestVerdict, AssistantVersionDocument]] = []
    for version in assistant_version_repo.list_by_business(business_id):
        if version.autotest_verdict is not None:
            verdicts.append((version.autotest_verdict, version))

    if not verdicts:
        return {}

    verdict, version = max(verdicts, key=lambda pair: int(pair[0].finished_at))
    run: AutotestRunDocument | None = autotest_run_repo.get(business_id, verdict.run_id)
    if run is None:
        return {}

    return {
        result.autotest_case_id: to_result_view(
            run, version, result, verdict.finished_at
        )
        for result in run.results
        if result.autotest_case_id is not None
    }


def to_result_view(
    run: AutotestRunDocument,
    version: AssistantVersionDocument,
    result: AutotestScenarioResult,
    checked_at: Microseconds,
) -> AutotestCaseResultView:
    answer: MessageText | None = next(
        (
            line.text
            for line in result.transcript
            if line.author is MessageAuthor.ASSISTANT
        ),
        None,
    )
    return AutotestCaseResultView(
        run_id=run.id,
        assistant_version_number=version.version_number,
        outcome=result.outcome,
        check_codes=list(result.check_codes),
        answer=answer,
        checked_at=checked_at,
    )
