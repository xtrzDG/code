from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import (
    AssistantVersionRepoContract,
    AuditLogRepoContract,
    UserRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import (
    AssistantVersionRefusalCode,
    AssistantVersionStatus,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants import (
    AssistantVersionActivation,
    AssistantVersionDetails,
    PublishAssistantVersionCommand,
)
from app.schemas.dto.go_live import (
    GoLiveCheck,
    GoLiveReadiness,
    GoLiveReadinessRequest,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.assembly.go_live_refusals import (
    build_check_reason,
    build_version_reason,
    describe_go_live_refusal,
    find_blocking_failures,
)

UNTESTED_STATUSES: frozenset[AssistantVersionStatus] = frozenset(
    {AssistantVersionStatus.DRAFT, AssistantVersionStatus.TESTS_FAILED}
)


class PublishAssistantVersionUseCase(
    UseCaseContract[PublishAssistantVersionCommand, AssistantVersionDetails]
):
    """
    Owner switches the assistant to a version ("Включить", concept section 4).

    A READY version is published. A DRAFT or TESTS_FAILED one breaks the
    launch rule ("a broken version does not reach customers"), so only a
    platform admin may force it with accept_failed_tests, and that decision
    is written to the audit log. A version under test, an already published
    one and an archived one (use rollback) are conflicts.

    Every refusal carries machine-readable reasons: an untested version or
    one under test is refused with all failed go-live checks at once (the
    "autotests" check first in line with the others), a live or archived one
    with an AssistantVersionRefusalCode.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        assistant_version_repo: AssistantVersionRepoContract,
        check_go_live_readiness: UseCaseContract[
            GoLiveReadinessRequest, GoLiveReadiness
        ],
        activate_assistant_version: UseCaseContract[
            AssistantVersionActivation,
            AssistantVersionDocument,
        ],
        version_details_transformer: TransformerContract[
            AssistantVersionDocument,
            AssistantVersionDetails,
        ],
        user_repo: UserRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._check_go_live_readiness: UseCaseContract[
            GoLiveReadinessRequest, GoLiveReadiness
        ] = check_go_live_readiness
        self._activate_assistant_version: UseCaseContract[
            AssistantVersionActivation,
            AssistantVersionDocument,
        ] = activate_assistant_version
        self._version_details_transformer: TransformerContract[
            AssistantVersionDocument,
            AssistantVersionDetails,
        ] = version_details_transformer
        self._user_repo: UserRepoContract = user_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(
        self, input_data: PublishAssistantVersionCommand
    ) -> AssistantVersionDetails:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id,
            input_data.version_id,
        )
        if version is None:
            raise NotFoundError(
                f"Assistant version {input_data.version_id} was not found."
            )

        is_forced: bool = self._require_publishable(business, version, input_data)
        published_version: AssistantVersionDocument = (
            self._activate_assistant_version.run(
                AssistantVersionActivation(business=business, version=version)
            )
        )
        if is_forced:
            now: Microseconds = self._wall_clock.now_unix()
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    actor_id=input_data.user_id,
                    action=AuditAction.PUBLISH_UNTESTED,
                    entity=AuditEntityName("assistant_version"),
                    entity_id=AuditEntityReference(str(version.id)),
                    created_at=now,
                    updated_at=now,
                )
            )

        return self._version_details_transformer.transform(published_version)

    def _require_publishable(
        self,
        business: BusinessDocument,
        version: AssistantVersionDocument,
        command: PublishAssistantVersionCommand,
    ) -> bool:
        """True when an untested version is forced live by a platform admin."""

        if version.status is AssistantVersionStatus.READY:
            return False

        if version.status in UNTESTED_STATUSES and command.accept_failed_tests:
            if not self._is_platform_admin(command.user_id):
                message: str = (
                    "Only a platform admin may publish a version that has not "
                    "passed the autotests (accept_failed_tests)."
                )
                raise AccessDeniedError(
                    message,
                    reasons=[
                        build_version_reason(
                            AssistantVersionRefusalCode.FORCE_PUBLISH_ADMIN_ONLY,
                            message,
                        )
                    ],
                )

            return True

        if version.status in UNTESTED_STATUSES or (
            version.status is AssistantVersionStatus.TESTING
        ):
            readiness: GoLiveReadiness = self._check_go_live_readiness.run(
                GoLiveReadinessRequest(business=business, version=version)
            )
            failures: list[GoLiveCheck] = find_blocking_failures(readiness)
            raise ConflictError(
                describe_go_live_refusal(failures),
                reasons=[build_check_reason(check) for check in failures],
            )

        if version.status is AssistantVersionStatus.PUBLISHED:
            message = f"Version {version.version_number} is already live."
            raise ConflictError(
                message,
                reasons=[
                    build_version_reason(
                        AssistantVersionRefusalCode.VERSION_ALREADY_LIVE, message
                    )
                ],
            )

        message = (
            f"Version {version.version_number} is archived; use rollback to "
            "publish it again."
        )
        raise ConflictError(
            message,
            reasons=[
                build_version_reason(
                    AssistantVersionRefusalCode.VERSION_ARCHIVED, message
                )
            ],
        )

    def _is_platform_admin(self, user_id: UserId) -> bool:
        user: UserDocument | None = self._user_repo.get(user_id)
        return user is not None and bool(user.is_platform_admin)
