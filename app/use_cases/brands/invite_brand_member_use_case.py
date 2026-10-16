from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.brands import BrandDocument, BrandMember
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.brands.brand_commands import (
    BrandAccessRequest,
    InviteBrandMemberCommand,
)
from app.schemas.dto.brands.brand_views import BrandView, BrandViewSource
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.use_cases.brands.brand_audit import BRAND_MEMBER_ENTITY, record_in_locations
from app.use_cases.brands.brand_rules import assigned_locations, reached_locations
from app.use_cases.brands.brand_view_loading import BrandViewLoader
from app.use_cases.shared.team_invitations import (
    clean_display_name,
    find_or_create_invited_user,
)


class InviteBrandMemberUseCase(UseCaseContract[InviteBrandMemberCommand, BrandView]):
    """
    A brand owner adds a person to the brand's team (after a fresh
    sign-in), by phone number or e-mail, as another owner or as a regional
    manager of some of the brand's locations. A person without an account
    gets an unverified one in the first location's owner language (a
    national phone number is read in its country). Each location the
    person now reaches records it in its audit log.
    """

    def __init__(
        self,
        authorize_brand_access: UseCaseContract[BrandAccessRequest, BrandDocument],
        brand_repo: BrandRepoContract,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        phone_number_parser: PhoneNumberParserContract,
        audit_log_repo: AuditLogRepoContract,
        brand_view_transformer: TransformerContract[BrandViewSource, BrandView],
        step_up: StepUpGuardContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_brand_access: UseCaseContract[
            BrandAccessRequest, BrandDocument
        ] = authorize_brand_access
        self._brand_repo: BrandRepoContract = brand_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._user_repo: UserRepoContract = user_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._step_up: StepUpGuardContract = step_up
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._views: BrandViewLoader = BrandViewLoader(
            business_repo, user_repo, brand_view_transformer
        )

    def run(self, input_data: InviteBrandMemberCommand) -> BrandView:
        brand: BrandDocument = self._authorize_brand_access.run(
            BrandAccessRequest(
                user_id=input_data.user_id,
                brand_id=input_data.brand_id,
                required_role=BrandMemberRole.BRAND_OWNER,
            )
        )
        invitation = input_data.invitation
        locations: list[BusinessDocument] = self._business_repo.list_by_brand(brand.id)
        location_ids: list[BusinessId] = [location.id for location in locations]
        assigned: list[BusinessId] = assigned_locations(
            invitation.role, invitation.business_ids, location_ids
        )
        if not locations:
            raise ConflictError("Add a location to the brand first.")

        display_name = clean_display_name(invitation.display_name)
        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()
        person: UserDocument = find_or_create_invited_user(
            self._user_repo,
            self._phone_number_parser,
            invitation.phone_number,
            invitation.email,
            invitation.country_hint or locations[0].country_code,
            locations[0].owner_language,
            display_name,
            now,
        )

        def add(current: BrandDocument) -> None:
            if any(member.user_id == person.id for member in current.members):
                raise ConflictError("This person is already on the brand's team.")

            current.members = [
                *current.members,
                BrandMember(
                    user_id=person.id, role=invitation.role, business_ids=assigned
                ),
            ]
            current.updated_at = now

        updated: BrandDocument = self._brand_repo.update(brand.id, add)
        record_in_locations(
            self._audit_log_repo,
            reached_locations(invitation.role, assigned, location_ids),
            input_data.user_id,
            AuditAction.CREATE,
            BRAND_MEMBER_ENTITY,
            AuditEntityReference(str(person.id)),
            input_data.client_ip_address,
            now,
        )
        return self._views.load(updated, input_data.user_id)
