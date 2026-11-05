from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.referral_repositories import PartnerRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.storage import StorageReadSessionContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.domain.users import UserDocument
from app.schemas.dto.brands.brand_reach import BusinessReach
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.users import CurrentUserView, UserMembershipView, UserView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.brand_reach import reachable_businesses
from app.use_cases.shared.storage_transaction import in_read_session
from app.utilities.referrals.partner_identity import find_partner_of
from app.utilities.security.admin_permissions import permissions_of


class GetCurrentUserUseCase(UseCaseContract[UserId, CurrentUserView]):
    """
    Return the signed-in user and their businesses, oldest business first
    (those their brands give them too, named with the brand), and how the
    current session is signed in. `is_platform_admin`, the
    admin role and its permissions follow the admin team of now, so the
    cabinet stops offering the admin pages to someone taken off it and
    shows each admin only the pages their role opens. `is_partner` says
    the person signs in with a partner's phone number or e-mail (the
    cabinet offers the partner portal). The reads (the person, the admin
    team, the businesses, the partner) share one read session.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        business_repo: BusinessRepoContract,
        brand_repo: BrandRepoContract,
        user_view_transformer: TransformerContract[UserDocument, UserView],
        session_assurance: SessionAssuranceContract,
        platform_admins: PlatformAdminRegistryContract,
        partner_repo: PartnerRepoContract,
        read_session: StorageReadSessionContract | None = None,
    ) -> None:
        self._partner_repo: PartnerRepoContract = partner_repo
        self._user_repo: UserRepoContract = user_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._brand_repo: BrandRepoContract = brand_repo
        self._user_view_transformer: TransformerContract[UserDocument, UserView] = (
            user_view_transformer
        )
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._platform_admins: PlatformAdminRegistryContract = platform_admins
        self._read_session: StorageReadSessionContract | None = read_session

    def run(self, input_data: UserId) -> CurrentUserView:
        with in_read_session(self._read_session):
            return self._run(input_data)

    def _run(self, input_data: UserId) -> CurrentUserView:
        stored: UserDocument | None = self._user_repo.get(input_data)
        if stored is None:
            raise NotFoundError(f"User {input_data} was not found.")

        role: PlatformAdminRole | None = self._platform_admins.role_of(stored)
        user: UserDocument = stored.model_copy(
            update={"is_platform_admin": role is not None}
        )
        reach: list[BusinessReach] = reachable_businesses(
            self._business_repo, self._brand_repo, user.id
        )
        memberships: list[UserMembershipView] = [
            UserMembershipView(
                business_id=item.business.id,
                business_name=item.business.name,
                role=item.role,
                business_status=item.business.status,
                country_code=item.business.country_code,
                brand_id=item.business.brand_id,
                brand_name=None if item.brand is None else item.brand.name,
            )
            for item in reach
        ]
        assurance: SessionAssurance | None = self._session_assurance.current()
        return CurrentUserView(
            user=self._user_view_transformer.transform(user),
            memberships=memberships,
            auth_level=assurance.auth_level
            if assurance is not None and assurance.user_id == user.id
            else None,
            platform_admin_role=role,
            platform_admin_permissions=permissions_of(role),
            is_partner=find_partner_of(self._partner_repo, user) is not None,
        )
