import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.feature_flags import FeatureFlagRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.feature_flags import FeatureFlagDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.feature_flags import FeatureFlagCommand, FeatureFlagView
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.access.constrained_strings import AdminActionReason
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.admin.feature_flags.feature_flag_views import (
    build_flag_view,
    require_definition,
)
from app.utilities.feature_flags.feature_flag_catalog import FeatureFlagDefinition

logger: logging.Logger = logging.getLogger(__name__)
AUDITED_ENTITY: AuditEntityName = AuditEntityName("feature_flag")


class SetFeatureFlagUseCase(UseCaseContract[FeatureFlagCommand, FeatureFlagView]):
    """
    PUT /v1/admin/feature-flags/{flag_name}: a SUPER platform admin
    (MANAGE_OPERATIONS) sets the whole state of a registry flag after a
    recent sign-in (step-up): on or off, the rollout percentage, the
    businesses it always and never holds for, and why. The gate reads the
    new state at the next request of every process. Every change is
    written to the platform's audit log (UPDATE of `feature_flag`, the
    flag's name, with the reason and the address) and logged.

    Raises:
        AccessDeniedError: the user is not a SUPER platform admin.
        StepUpRequiredError: the session did not prove its person lately.
        NotFoundError: the registry lists no flag of that name.
        ValidationFailedError: a business on both lists.
        ConflictError: the flag already stands exactly so.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        flag_repo: FeatureFlagRepoContract,
        audit_log_repo: AuditLogRepoContract,
        step_up: StepUpGuardContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._flag_repo: FeatureFlagRepoContract = flag_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._step_up: StepUpGuardContract = step_up
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: FeatureFlagCommand) -> FeatureFlagView:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_OPERATIONS,
            )
        )
        self._step_up.require_recent_authentication()
        definition: FeatureFlagDefinition = require_definition(input_data.name)
        request = input_data.request
        both = set(request.included_business_ids) & set(request.excluded_business_ids)
        if both:
            raise ValidationFailedError(
                "A business is either included or excluded: "
                + ", ".join(sorted(str(business_id) for business_id in both))
            )

        stored: FeatureFlagDocument | None = self._flag_repo.get(definition.name)
        if stored is not None and is_unchanged(stored, input_data):
            raise ConflictError(f"The feature flag {definition.name} stands so.")

        now: Microseconds = self._wall_clock.now_unix()
        flag = FeatureFlagDocument(
            name=definition.name,
            is_enabled=request.is_enabled,
            rollout_percent=request.rollout_percent,
            included_business_ids=list(dict.fromkeys(request.included_business_ids)),
            excluded_business_ids=list(dict.fromkeys(request.excluded_business_ids)),
            reason=request.reason,
            changed_by=admin.id,
            changed_at=now,
            created_at=now if stored is None else stored.created_at,
            updated_at=now,
        )
        self._flag_repo.save(flag)
        entry = AuditLogEntryDocument(
            actor_id=admin.id,
            action=AuditAction.UPDATE,
            entity=AUDITED_ENTITY,
            entity_id=AuditEntityReference(str(definition.name)),
            ip_address=input_data.client_ip_address,
            reason=AdminActionReason(str(request.reason)),
            created_at=now,
            updated_at=now,
        )
        self._audit_log_repo.append(entry)
        # The reason stays in the audit log; free text never goes to the logs.
        logger.warning(
            "Feature flag %s set to %s at %s%% by platform admin %s (audit entry %s)",
            definition.name,
            "on" if flag.is_enabled else "off",
            int(flag.rollout_percent),
            admin.id,
            entry.id,
        )
        return build_flag_view(definition, flag)


def is_unchanged(stored: FeatureFlagDocument, command: FeatureFlagCommand) -> bool:
    request = command.request
    return (
        stored.is_enabled == request.is_enabled
        and int(stored.rollout_percent) == int(request.rollout_percent)
        and set(stored.included_business_ids) == set(request.included_business_ids)
        and set(stored.excluded_business_ids) == set(request.excluded_business_ids)
    )
