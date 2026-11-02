import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_safety import (
    PlatformPauseRepoContract,
    PlatformSpendGaugeContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.spend_guard_settings import SpendGuardSettings
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.platform_pauses import PlatformPauseDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.platform_pause import PlatformPauseCommand, PlatformPauseView
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.access.constrained_strings import AdminActionReason
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.spend_guard.platform_pause.platform_pause_views import (
    build_platform_pause_view,
)
from app.utilities.spend.platform_brakes import (
    read_budget_stop,
)

logger: logging.Logger = logging.getLogger(__name__)
AUDITED_ENTITY: AuditEntityName = AuditEntityName("platform_pause")
PAUSED: AuditEntityReference = AuditEntityReference("paused")
RESUMED: AuditEntityReference = AuditEntityReference("resumed")


class SetPlatformPauseUseCase(UseCaseContract[PlatformPauseCommand, PlatformPauseView]):
    """
    A SUPER platform admin (MANAGE_OPERATIONS, which only SUPER holds)
    pauses every assistant at once, or resumes them, with a reason, after
    a recent sign-in (step-up).

    While paused, the spend guard holds every model turn back: customers
    hear in their language that a colleague takes over (and staff get the
    handoff), and the voice platform refuses calls, which the carrier
    forwards to the business's staff phone. Resuming lifts it at once; no
    business setting changes either way. Every change is written to the
    platform's audit log (UPDATE of `platform_pause`, `paused` or
    `resumed`, with the reason and the address) and logged as a warning.

    Raises:
        AccessDeniedError: the user is not a SUPER platform admin.
        StepUpRequiredError: the session did not prove its person lately.
        ConflictError: the platform is already paused (or running).
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        platform_pause_repo: PlatformPauseRepoContract,
        platform_spend_gauge: PlatformSpendGaugeContract,
        audit_log_repo: AuditLogRepoContract,
        step_up: StepUpGuardContract,
        settings: SpendGuardSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._pause_repo: PlatformPauseRepoContract = platform_pause_repo
        self._spend_gauge: PlatformSpendGaugeContract = platform_spend_gauge
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._step_up: StepUpGuardContract = step_up
        self._settings: SpendGuardSettings = settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PlatformPauseCommand) -> PlatformPauseView:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_OPERATIONS,
            )
        )
        self._step_up.require_recent_authentication()
        request = input_data.request
        stored: PlatformPauseDocument | None = self._pause_repo.get()
        is_paused: bool = stored is not None and stored.is_paused
        if is_paused == request.is_paused:
            raise ConflictError(
                "Every assistant is already paused."
                if is_paused
                else "The assistants are not paused."
            )

        now: Microseconds = self._wall_clock.now_unix()
        pause = PlatformPauseDocument(
            is_paused=request.is_paused,
            reason=request.reason,
            changed_by=admin.id,
            changed_at=now,
            created_at=now if stored is None else stored.created_at,
            updated_at=now,
        )
        self._pause_repo.save(pause)
        entry = AuditLogEntryDocument(
            actor_id=admin.id,
            action=AuditAction.UPDATE,
            entity=AUDITED_ENTITY,
            entity_id=PAUSED if request.is_paused else RESUMED,
            ip_address=input_data.client_ip_address,
            reason=AdminActionReason(str(request.reason)),
            created_at=now,
            updated_at=now,
        )
        self._audit_log_repo.append(entry)
        # The reason stays in the audit log; free text never goes to the logs.
        logger.warning(
            "Every assistant %s by platform admin %s (audit entry %s)",
            "paused" if request.is_paused else "resumed",
            admin.id,
            entry.id,
        )
        return build_platform_pause_view(
            pause,
            read_budget_stop(self._spend_gauge, self._settings, now),
            self._settings,
        )
