from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.repositories.autotest_case_repositories import (
    AutotestCaseRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.setup_repositories import AssistantApplyRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.setup import (
    ApplyAttentionCode,
    ApplyChangesStage,
    SetupActionTarget,
)
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.setup import ApplyAttentionReason, AssistantApplyDocument
from app.schemas.dto.assistants.autotest_cases import OwnerCheckOutcomeView
from app.schemas.dto.setup.apply_changes import (
    ApplyAttentionView,
    ApplyChangesSource,
    ApplyChangesView,
    SetupActionView,
)
from app.schemas.dto.setup.pending_changes import PendingChange, PendingChangesRequest
from app.schemas.typings.assistants.constrained_integers import AutotestScenarioCount
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.setup.strings import ApplyAttentionMessage, SetupActionLabel
from app.use_cases.shared.owner_check_outcomes import list_failed_owner_checks
from app.utilities.assembly.autotest_evaluation import count_run_scenarios
from app.utilities.setup.apply_attention import ATTENTION_TARGETS, ATTENTION_TEXTS
from app.utilities.setup.setup_texts import ACTION_LABELS

RUNNING_STAGES: frozenset[ApplyChangesStage] = frozenset(
    {
        ApplyChangesStage.BUILDING,
        ApplyChangesStage.CHECKING,
        ApplyChangesStage.PUBLISHING,
    }
)


class DescribeApplyChangesUseCase(
    UseCaseContract[ApplyChangesSource, ApplyChangesView]
):
    """
    Where "Apply changes" of a business stands, in the owner's words:
    the stage, how many automatic checks have run, why it needs attention
    (each reason with where to fix it), and whether anything the
    assistant is built from changed since the live version (the same
    changes GET /assistant/pending-changes lists). A version whose
    checks finished while the worker has not published it yet shows as
    PUBLISHING. Failed checks name the owner's own checks the version did
    not pass, each with its question and why, as asked.
    """

    def __init__(
        self,
        assistant_apply_repo: AssistantApplyRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        collect_pending_changes: UseCaseContract[
            PendingChangesRequest, list[PendingChange]
        ],
        localized_text_resolver: LocalizedTextResolverContract,
        autotest_case_repo: AutotestCaseRepoContract,
    ) -> None:
        self._assistant_apply_repo: AssistantApplyRepoContract = assistant_apply_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._collect_pending_changes: UseCaseContract[
            PendingChangesRequest, list[PendingChange]
        ] = collect_pending_changes
        self._resolver: LocalizedTextResolverContract = localized_text_resolver
        self._autotest_case_repo: AutotestCaseRepoContract = autotest_case_repo

    def run(self, input_data: ApplyChangesSource) -> ApplyChangesView:
        business: BusinessDocument = input_data.business
        apply: AssistantApplyDocument | None = (
            self._assistant_apply_repo.get_by_business(business.id)
        )
        version: AssistantVersionDocument | None = (
            None
            if apply is None or apply.assistant_version_id is None
            else self._assistant_version_repo.get(
                business.id, apply.assistant_version_id
            )
        )
        has_changes: bool = self._has_changes(business)
        if apply is None:
            return ApplyChangesView(
                business_id=business.id,
                is_in_progress=False,
                has_unapplied_changes=has_changes,
            )

        stage: ApplyChangesStage = shown_stage(apply, version)
        run: AutotestRunDocument | None = (
            None
            if version is None or version.autotest_run_id is None
            else self._autotest_run_repo.get(business.id, version.autotest_run_id)
        )
        is_checking: bool = stage is ApplyChangesStage.CHECKING and run is not None
        failed_checks: list[OwnerCheckOutcomeView] = (
            self._failed_owner_checks(business, run, input_data.language)
            if run is not None
            and any(
                reason.code is ApplyAttentionCode.CHECKS_FAILED
                for reason in apply.attention
            )
            else []
        )
        return ApplyChangesView(
            business_id=business.id,
            stage=stage,
            is_in_progress=stage in RUNNING_STAGES,
            has_unapplied_changes=has_changes,
            assistant_version_id=apply.assistant_version_id,
            version_number=None if version is None else version.version_number,
            checks_done=(
                AutotestScenarioCount(len(run.results))
                if is_checking and run is not None
                else None
            ),
            checks_total=(
                count_run_scenarios(run) if is_checking and run is not None else None
            ),
            started_at=apply.started_at,
            finished_at=apply.finished_at,
            attention=[
                self._attention(reason, failed_checks, input_data.language)
                for reason in apply.attention
            ],
        )

    def _attention(
        self,
        reason: ApplyAttentionReason,
        failed_checks: list[OwnerCheckOutcomeView],
        language: LanguageTag,
    ) -> ApplyAttentionView:
        return ApplyAttentionView(
            code=reason.code,
            message=ApplyAttentionMessage(
                self._resolver.resolve(ATTENTION_TEXTS[reason.code], language)
            ),
            details=list(reason.details),
            action=self._action(reason.code, language),
            failed_checks=(
                failed_checks if reason.code is ApplyAttentionCode.CHECKS_FAILED else []
            ),
        )

    def _failed_owner_checks(
        self,
        business: BusinessDocument,
        run: AutotestRunDocument,
        language: LanguageTag,
    ) -> list[OwnerCheckOutcomeView]:
        cases: dict[AutotestCaseId, AutotestCaseDocument] = {
            case.id: case
            for case in self._autotest_case_repo.list_by_business(business.id)
        }
        return list_failed_owner_checks(
            self._resolver, run, cases, run.updated_at, language
        )

    def _action(
        self, code: ApplyAttentionCode, language: LanguageTag
    ) -> SetupActionView:
        target: SetupActionTarget = ATTENTION_TARGETS[code]
        return SetupActionView(
            target=target,
            label=SetupActionLabel(
                self._resolver.resolve(ACTION_LABELS[target], language)
            ),
        )

    def _has_changes(self, business: BusinessDocument) -> bool:
        live: AssistantVersionDocument | None = (
            None
            if business.published_assistant_version_id is None
            else self._assistant_version_repo.get(
                business.id, business.published_assistant_version_id
            )
        )
        if live is None:
            # Nothing is live yet: a profile is something to launch.
            return self._business_profile_repo.get_by_business(business.id) is not None

        return bool(
            self._collect_pending_changes.run(
                PendingChangesRequest(
                    business=business,
                    version=live,
                    language=business.owner_language,
                )
            )
        )


def shown_stage(
    apply: AssistantApplyDocument,
    version: AssistantVersionDocument | None,
) -> ApplyChangesStage:
    """
    The stored stage, except a CHECKING apply whose checks are over: it is
    PUBLISHING until the worker has published it (or found the failure).
    """

    if (
        apply.stage is ApplyChangesStage.CHECKING
        and version is not None
        and version.status is not AssistantVersionStatus.TESTING
    ):
        return ApplyChangesStage.PUBLISHING

    return apply.stage
