import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.setup_repositories import AssistantApplyRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.setup import ApplyAttentionCode, ApplyChangesStage
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.setup import ApplyAttentionReason, AssistantApplyDocument
from app.schemas.dto.assistants.assembly_sources import AssistantVersionActivation
from app.schemas.dto.setup.apply_changes import AppliedVersion
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.assistants.apply.apply_records import move_apply
from app.utilities.setup.apply_attention import (
    attention_from_refusal,
    failed_scenario_kinds,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
WAITING_STAGES: frozenset[ApplyChangesStage] = frozenset(
    {ApplyChangesStage.CHECKING, ApplyChangesStage.PUBLISHING}
)
VERSION_AUDIT_ENTITY: AuditEntityName = AuditEntityName("assistant_version")


class PublishAppliedVersionUseCase(UseCaseContract[AppliedVersion, None]):
    """
    The last stage of "Apply changes", run by the worker when the checks of
    the applied version finish (and in the request for a version that was
    checked already): a READY version goes live through the same
    activation as publishing (every launch condition checked again, the
    trial starting at the first go-live) and the apply is LIVE; failed or
    interrupted checks, or a refused launch, leave it NEEDS_ATTENTION with
    plain reasons. Only the business's current apply of this very version
    is acted on, so a run of an older apply or a manual check from Advanced
    changes nothing. Publishing is written to the audit log in the name of
    the owner who applied.
    """

    def __init__(
        self,
        assistant_apply_repo: AssistantApplyRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        business_repo: BusinessRepoContract,
        activate_assistant_version: UseCaseContract[
            AssistantVersionActivation,
            AssistantVersionDocument,
        ],
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._assistant_apply_repo: AssistantApplyRepoContract = assistant_apply_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._activate_assistant_version: UseCaseContract[
            AssistantVersionActivation,
            AssistantVersionDocument,
        ] = activate_assistant_version
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AppliedVersion) -> None:
        apply: AssistantApplyDocument | None = (
            self._assistant_apply_repo.get_by_business(input_data.business_id)
        )
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            input_data.business_id, input_data.assistant_version_id
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if (
            apply is None
            or apply.stage not in WAITING_STAGES
            or apply.assistant_version_id != input_data.assistant_version_id
            or version is None
            or business is None
        ):
            return

        match version.status:
            case AssistantVersionStatus.TESTING:
                return
            case AssistantVersionStatus.READY:
                self._publish(business, version, apply)
            case AssistantVersionStatus.PUBLISHED:
                self._move(version, ApplyChangesStage.LIVE)
            case AssistantVersionStatus.TESTS_FAILED:
                run: AutotestRunDocument | None = (
                    None
                    if version.autotest_run_id is None
                    else self._autotest_run_repo.get(
                        business.id, version.autotest_run_id
                    )
                )
                self._move(
                    version,
                    ApplyChangesStage.NEEDS_ATTENTION,
                    [
                        ApplyAttentionReason(
                            code=ApplyAttentionCode.CHECKS_FAILED,
                            details=failed_scenario_kinds(run),
                        )
                    ],
                )
            case AssistantVersionStatus.DRAFT | AssistantVersionStatus.ARCHIVED:
                self._move(
                    version,
                    ApplyChangesStage.NEEDS_ATTENTION,
                    [ApplyAttentionReason(code=ApplyAttentionCode.CHECKS_STOPPED)],
                )

    def _publish(
        self,
        business: BusinessDocument,
        version: AssistantVersionDocument,
        apply: AssistantApplyDocument,
    ) -> None:
        self._move(version, ApplyChangesStage.PUBLISHING)
        try:
            self._activate_assistant_version.run(
                AssistantVersionActivation(business=business, version=version)
            )
        except ExternalServiceError:
            LOGGER.warning(
                "Applied version %s of business %s could not be published: the "
                "voice agent could not be set up.",
                version.id,
                business.id,
                exc_info=True,
            )
            self._move(
                version,
                ApplyChangesStage.NEEDS_ATTENTION,
                [ApplyAttentionReason(code=ApplyAttentionCode.VOICE_NOT_READY)],
            )
            return
        except ApplicationError as refusal:
            self._move(
                version,
                ApplyChangesStage.NEEDS_ATTENTION,
                attention_from_refusal(refusal),
            )
            return

        now: Microseconds = self._wall_clock.now_unix()
        self._move(version, ApplyChangesStage.LIVE)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=apply.requested_by,
                action=AuditAction.UPDATE,
                entity=VERSION_AUDIT_ENTITY,
                entity_id=AuditEntityReference(str(version.id)),
                created_at=now,
                updated_at=now,
            )
        )

    def _move(
        self,
        version: AssistantVersionDocument,
        stage: ApplyChangesStage,
        attention: list[ApplyAttentionReason] | None = None,
    ) -> None:
        move_apply(
            self._assistant_apply_repo,
            version.business_id,
            version.id,
            stage,
            self._wall_clock.now_unix(),
            attention or [],
        )
