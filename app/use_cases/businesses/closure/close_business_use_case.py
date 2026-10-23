from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
    BusinessDeletionRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.business_closures import (
    BusinessClosureReason,
    ClosureNoticeKind,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.business_closures.closure_views import (
    BusinessClosureView,
    CloseBusinessCommand,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.businesses.closure.closure_effects import ClosureEffects
from app.use_cases.businesses.closure.closure_notices import ClosureNotices
from app.use_cases.businesses.closure.closure_reads import is_owner_of
from app.use_cases.businesses.closure.closure_rules import (
    deletion_moment,
    is_cancel_under_way,
    require_name_confirmation,
)
from app.use_cases.businesses.closure.closure_views import closure_view
from app.utilities.business_closures.closure_identity import closure_id_for

CLOSURE_ENTITY: AuditEntityName = AuditEntityName("business_closure")


class CloseBusinessUseCase(UseCaseContract[CloseBusinessCommand, BusinessClosureView]):
    """
    An owner closes the business (after a fresh sign-in, typing its name):
    it is pending deletion for 30 days. The assistant is paused, the
    channels are off, automatic charges stop (`ClosureEffects`), every owner
    is told when the data goes and how to keep it, and the business's audit
    log records who closed it. The full export stays available all along,
    and any owner may cancel until the deletion begins. Closing twice (two
    owners at once, a retried request) opens one closure; the second request
    applies the same effects again and answers the same view.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        step_up: StepUpGuardContract,
        closure_repo: BusinessClosureRepoContract,
        deletion_repo: BusinessDeletionRepoContract,
        effects: ClosureEffects,
        notices: ClosureNotices,
        audit_log_repo: AuditLogRepoContract,
        brand_repo: BrandRepoContract,
        user_repo: UserRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._step_up: StepUpGuardContract = step_up
        self._closure_repo: BusinessClosureRepoContract = closure_repo
        self._deletion_repo: BusinessDeletionRepoContract = deletion_repo
        self._effects: ClosureEffects = effects
        self._notices: ClosureNotices = notices
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._brand_repo: BrandRepoContract = brand_repo
        self._user_repo: UserRepoContract = user_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CloseBusinessCommand) -> BusinessClosureView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        self._step_up.require_recent_authentication()
        require_name_confirmation(business, input_data.confirmation_name)
        if self._deletion_repo.find_by_business(business.id) is not None:
            raise ConflictError("The business is being deleted already.")

        now: Microseconds = self._wall_clock.now_unix()
        opened: bool = self._open(
            BusinessClosureDocument(
                id=closure_id_for(business.id),
                business_id=business.id,
                reason=BusinessClosureReason.OWNER_REQUEST,
                requested_by=input_data.user_id,
                requested_at=now,
                delete_after=deletion_moment(now),
                status_before=business.status,
                created_at=now,
                updated_at=now,
            )
        )
        closure: BusinessClosureDocument = self._apply_effects(business, now)
        if opened:
            self._record(business, input_data, now)
            self._notices.send(
                business, closure, ClosureNoticeKind.OPENED_BY_OWNER, input_data.user_id
            )

        return closure_view(
            business.id,
            closure,
            self._user_repo,
            is_owner_of(self._brand_repo, business, input_data.user_id),
            False,
        )

    def _open(self, closure: BusinessClosureDocument) -> bool:
        """
        Open the closure. A cancelled one is a cancel still restoring the
        business (refused: its last step removes the closure, which would
        take a new one with it) or, past CANCEL_LEASE, one that died, which
        goes first.
        """

        if self._closure_repo.open(closure):
            return True

        existing: BusinessClosureDocument | None = self._closure_repo.get(
            closure.business_id
        )
        if existing is None or existing.cancelled_at is None:
            return False

        if is_cancel_under_way(existing, closure.requested_at):
            raise ConflictError(
                "The closure is being cancelled right now; try again in a few minutes."
            )

        self._closure_repo.remove(closure.business_id)
        return self._closure_repo.open(closure)

    def _apply_effects(
        self, business: BusinessDocument, now: Microseconds
    ) -> BusinessClosureDocument:
        self._effects.pause(business.id, now)
        disconnected: list[ChannelId] = self._effects.disconnect_channels(
            business.id, now
        )
        self._effects.stop_billing(business.id, now)

        def remember(closure: BusinessClosureDocument) -> BusinessClosureDocument:
            closure.disconnected_channel_ids = list(
                dict.fromkeys([*closure.disconnected_channel_ids, *disconnected])
            )
            closure.updated_at = now
            return closure

        stored: BusinessClosureDocument | None = self._closure_repo.modify(
            business.id, remember
        )
        if stored is None:
            raise ConflictError("The closure was cancelled meanwhile; try again.")

        return stored

    def _record(
        self,
        business: BusinessDocument,
        input_data: CloseBusinessCommand,
        now: Microseconds,
    ) -> None:
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.CREATE,
                entity=CLOSURE_ENTITY,
                entity_id=AuditEntityReference(str(business.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
