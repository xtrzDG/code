from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.autotest_case_repositories import (
    AutotestCaseRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AutotestExpectation
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants.autotest_cases import (
    AutotestCaseChanges,
    AutotestCaseView,
    UpdateAutotestCaseCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.assistants.constrained_strings import (
    AutotestCaseQuestion,
    AutotestExpectedText,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.autotests.cases.autotest_case_rules import (
    check_expected_text,
    check_unique,
)
from app.use_cases.autotests.cases.autotest_case_views import to_case_view


class UpdateAutotestCaseUseCase(
    UseCaseContract[UpdateAutotestCaseCommand, AutotestCaseView]
):
    """
    Change one of the owner's checks (owner only): its question, what the
    answer must do, its language, or pause it (`is_active`: a paused check
    is kept but not played). Missing fields stay as they are. A check asked
    differently forgets its "Check now", which answered the old question.

    Raises:
        NotFoundError: the check is not this business's.
        ValidationFailedError: a text expectation without its text.
        ConflictError: the change makes it the same as another check.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        autotest_case_repo: AutotestCaseRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._autotest_case_repo: AutotestCaseRepoContract = autotest_case_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateAutotestCaseCommand) -> AutotestCaseView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        case: AutotestCaseDocument | None = self._autotest_case_repo.get(
            business.id, input_data.case_id
        )
        if case is None:
            raise NotFoundError(f"Check {input_data.case_id} was not found.")

        changes: AutotestCaseChanges = input_data.changes
        question: AutotestCaseQuestion = changes.question or case.question
        expectation: AutotestExpectation = changes.expectation or case.expectation
        expected_text: AutotestExpectedText | None = check_expected_text(
            expectation,
            changes.expected_text
            if changes.expected_text is not None
            else case.expected_text,
        )
        check_unique(
            self._autotest_case_repo.list_by_business(business.id),
            question,
            expectation,
            expected_text,
            own_id=case.id,
        )
        language: LanguageTag = changes.language or case.language
        is_same_question: bool = (
            question == case.question
            and expectation is case.expectation
            and expected_text == case.expected_text
            and language == case.language
        )
        changed: AutotestCaseDocument = case.model_copy(
            update={
                "question": question,
                "expectation": expectation,
                "expected_text": expected_text,
                "language": language,
                "is_active": (
                    case.is_active if changes.is_active is None else changes.is_active
                ),
                # "Check now" answered the check as it was asked.
                "last_probe": case.last_probe if is_same_question else None,
                "updated_at": self._wall_clock.now_unix(),
            }
        )
        self._autotest_case_repo.save(changed)
        return to_case_view(changed)
