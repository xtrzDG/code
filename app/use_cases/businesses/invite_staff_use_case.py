from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.businesses import (
    BusinessView,
    BusinessViewSource,
    InviteStaffCommand,
    InviteStaffRequest,
)
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.strings import UserDisplayName
from app.utilities.security.email_addresses import parse_email_address

MAX_DISPLAY_NAME_LENGTH: int = 100


class InviteStaffUseCase(UseCaseContract[InviteStaffCommand, BusinessView]):
    """
    Owner adds a team member by phone number (any country) or e-mail, as
    staff or as another owner.

    A person without an account gets an unverified one in the business's
    owner language; they confirm it by signing in with a code. Existing
    accounts are reused unchanged. The new membership is audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        phone_number_parser: PhoneNumberParserContract,
        audit_log_repo: AuditLogRepoContract,
        business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._business_repo: BusinessRepoContract = business_repo
        self._user_repo: UserRepoContract = user_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ] = business_view_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: InviteStaffCommand) -> BusinessView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        invitation: InviteStaffRequest = input_data.invitation
        display_name: UserDisplayName | None = invitation.display_name
        if display_name is not None:
            if len(display_name) > MAX_DISPLAY_NAME_LENGTH:
                raise ValidationFailedError(
                    "Display name must be at most "
                    f"{MAX_DISPLAY_NAME_LENGTH} characters."
                )

            if display_name.strip() == "":
                display_name = None

        now: Microseconds = self._wall_clock.now_unix()
        staff_user: UserDocument = self._find_or_create_user(
            invitation,
            business,
            display_name,
            now,
        )

        def add_member(current: BusinessDocument) -> None:
            # Checked and added on the business as stored now, so a change
            # saved meanwhile (settings, another member) is kept.
            if any(member.user_id == staff_user.id for member in current.members):
                raise ConflictError("This person is already a member of the business.")

            current.members = [
                *current.members,
                BusinessMember(user_id=staff_user.id, role=invitation.role),
            ]
            current.updated_at = now

        business = self._business_repo.update(business.id, add_member)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.CREATE,
                entity=AuditEntityName("business_member"),
                entity_id=AuditEntityReference(str(staff_user.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        member_users: list[UserDocument] = [
            user
            for member in business.members
            if (user := self._user_repo.get(member.user_id)) is not None
        ]
        return self._business_view_transformer.transform(
            BusinessViewSource(
                business=business,
                member_users=member_users,
                viewer_id=input_data.user_id,
            )
        )

    def _find_or_create_user(
        self,
        invitation: InviteStaffRequest,
        business: BusinessDocument,
        display_name: UserDisplayName | None,
        now: Microseconds,
    ) -> UserDocument:
        if invitation.phone_number is not None and invitation.email is None:
            phone_number: PhoneNumberDetails = self._phone_number_parser.parse(
                invitation.phone_number,
                invitation.country_hint or business.country_code,
            )
            existing_user: UserDocument | None = self._user_repo.find_by_phone_number(
                phone_number.e164
            )
            if existing_user is not None:
                return existing_user

            new_user = UserDocument(
                login_method=LoginMethod.PHONE,
                phone_number=phone_number.e164,
                country_code=phone_number.country_code,
                locale=business.owner_language,
                display_name=display_name,
                created_at=now,
                updated_at=now,
            )
            self._user_repo.save(new_user)
            return new_user

        if invitation.email is not None and invitation.phone_number is None:
            email: EmailAddress = parse_email_address(invitation.email)
            existing_email_user: UserDocument | None = self._user_repo.find_by_email(
                email
            )
            if existing_email_user is not None:
                return existing_email_user

            new_email_user = UserDocument(
                login_method=LoginMethod.EMAIL,
                email=email,
                locale=business.owner_language,
                display_name=display_name,
                created_at=now,
                updated_at=now,
            )
            self._user_repo.save(new_email_user)
            return new_email_user

        raise ValidationFailedError("Enter either a phone number or an e-mail.")
