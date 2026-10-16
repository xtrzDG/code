from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.repositories.autotest_case_repositories import (
    AutotestCaseRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants.autotest_cases import (
    AutotestCaseList,
    ListAutotestCasesQuery,
    OwnerCheckOutcomeView,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.autotests.cases.autotest_case_rules import AUTOTEST_CASE_LIMIT
from app.use_cases.autotests.cases.autotest_case_views import (
    latest_case_results,
    to_case_view,
)
from app.use_cases.shared.owner_check_outcomes import to_probe_view


class ListAutotestCasesUseCase(
    UseCaseContract[ListAutotestCasesQuery, AutotestCaseList]
):
    """
    "My checks" (owner only): the business's own checks, the first written
    first, each with how it did in the latest finished autotest run that
    played it (none yet for a check written after that run) and its
    latest "Check now" while the check has not changed since (the reason
    of a failure in `language`, the owner's language by default).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        autotest_case_repo: AutotestCaseRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._autotest_case_repo: AutotestCaseRepoContract = autotest_case_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._resolver: LocalizedTextResolverContract = localized_text_resolver

    def run(self, input_data: ListAutotestCasesQuery) -> AutotestCaseList:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        results = latest_case_results(
            self._assistant_version_repo, self._autotest_run_repo, business.id
        )
        language: LanguageTag = input_data.language or business.owner_language
        return AutotestCaseList(
            items=[
                to_case_view(
                    case, results.get(case.id), self._current_probe(case, language)
                )
                for case in self._autotest_case_repo.list_by_business(business.id)
            ],
            limit=AUTOTEST_CASE_LIMIT,
        )

    def _current_probe(
        self, case: AutotestCaseDocument, language: LanguageTag
    ) -> OwnerCheckOutcomeView | None:
        """The check's "Check now" unless the check changed after it."""

        probe = case.last_probe
        if probe is None or int(probe.checked_at) < int(case.updated_at):
            return None

        return to_probe_view(self._resolver, case, probe, language)
