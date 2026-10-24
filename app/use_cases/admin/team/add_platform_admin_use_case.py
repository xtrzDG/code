from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.platform_admins import (
    PlatformAdminCheck,
    PlatformAdminRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import (
    AddPlatformAdminCommand,
    PlatformAdminAccessRequest,
    PlatformAdminTeamView,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.use_cases.admin.team.admin_team import audit_team_change, team_view
from app.utilities.security.email_addresses import parse_email_address
from app.utilities.security.platform_admin_ids import derive_platform_admin_id

ONE_DESTINATION_MESSAGE: str = "Give exactly one of a phone number and an e-mail."
ALREADY_ADMIN_MESSAGE: str = "This person is already on the admin team."


class AddPlatformAdminUseCase(
    UseCaseContract[AddPlatformAdminCommand, PlatformAdminTeamView]
):
    """
    A SUPER admin adds a person to the admin team by the phone number
    (international format) or e-mail they sign in with, with a role. The
    person may not have signed in yet: their first sign-in asks them to set
    up an authenticator, which the admin pages need. Needs a fresh
    confirmation (step-up); audited as PLATFORM_ADMIN_CHANGED.
    """

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        platform_admin_repo: PlatformAdminRepoContract,
        user_repo: UserRepoContract,
        phone_number_parser: PhoneNumberParserContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        step_up: StepUpGuardContract,
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._platform_admin_repo: PlatformAdminRepoContract = platform_admin_repo
        self._user_repo: UserRepoContract = user_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._step_up: StepUpGuardContract = step_up

    def run(self, input_data: AddPlatformAdminCommand) -> PlatformAdminTeamView:
        actor: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_ADMINS,
            )
        )
        self._step_up.require_recent_authentication()
        record: PlatformAdminDocument = self._record(input_data, actor)
        if self._platform_admin_repo.get(record.id) is not None:
            raise ConflictError(ALREADY_ADMIN_MESSAGE)

        self._platform_admin_repo.save(record)
        audit_team_change(
            self._audit_log_repo,
            actor.id,
            record,
            input_data.client_ip_address,
            record.created_at,
        )
        return team_view(self._platform_admin_repo, self._user_repo, actor.id)

    def _record(
        self, command: AddPlatformAdminCommand, actor: UserDocument
    ) -> PlatformAdminDocument:
        now: Microseconds = self._wall_clock.now_unix()
        if command.phone_number is not None and command.email is None:
            phone = self._phone_number_parser.parse(command.phone_number, None).e164
            return PlatformAdminDocument(
                id=derive_platform_admin_id(LoginMethod.PHONE, phone),
                login_method=LoginMethod.PHONE,
                phone_number=phone,
                role=command.role,
                added_by=actor.id,
                created_at=now,
                updated_at=now,
            )

        if command.email is None or command.phone_number is not None:
            raise ValidationFailedError(ONE_DESTINATION_MESSAGE)

        email = parse_email_address(command.email)
        return PlatformAdminDocument(
            id=derive_platform_admin_id(LoginMethod.EMAIL, email),
            login_method=LoginMethod.EMAIL,
            email=email,
            role=command.role,
            added_by=actor.id,
            created_at=now,
            updated_at=now,
        )
