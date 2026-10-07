"""
A restaurant with an owner, staff and a customer, a platform support
admin, and support access wired as in production over the accounts
testbed: opening and leaving the cabinet, the owner's banner, consent and
ending, the expiry job.
"""

from collections.abc import Callable

from app.schemas.constants.access import BusinessAccessMode, PlatformAdminRole
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin import ClientCabinetAccess, OpenClientCabinetCommand
from app.schemas.dto.compliance import ContactDataCommand
from app.schemas.typings.access.constrained_strings import SupportAccessReason
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.access.close_client_cabinet_use_case import (
    CloseClientCabinetUseCase,
)
from app.use_cases.admin.access.end_expired_support_access_use_case import (
    EndExpiredSupportAccessUseCase,
)
from app.use_cases.admin.authorize_platform_admin_use_case import (
    AuthorizePlatformAdminUseCase,
)
from app.use_cases.admin.open_client_cabinet_use_case import OpenClientCabinetUseCase
from app.use_cases.businesses.support_access.end_support_access_use_case import (
    EndSupportAccessUseCase,
)
from app.use_cases.businesses.support_access.get_support_access_use_case import (
    GetSupportAccessUseCase,
)
from app.use_cases.businesses.support_access.update_support_write_access_use_case import (  # noqa: E501
    UpdateSupportWriteAccessUseCase,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.security.platform_admin_ids import derive_platform_admin_id
from tests.compliance.two_tenants import TwoTenants, seed_two_tenants
from tests.foundation.access_support import AllowStepUp
from tests.foundation.support_access_builders import RecordingStaffAlerts, as_request

SUPPORT_EMAIL: str = "support@platform.example"
SUPER_EMAIL: str = "boss@platform.example"
REASON: SupportAccessReason = SupportAccessReason("Owner asked why bookings stopped")
SUPPORT_IP: str = "198.51.100.40"


class SupportWorld:
    def __init__(
        self, support_role: PlatformAdminRole = PlatformAdminRole.SUPER
    ) -> None:
        self.tenants: TwoTenants = seed_two_tenants(
            {"PLATFORM_ADMIN_EMAILS": SUPER_EMAIL}
        )
        testbed = self.testbed = self.tenants.testbed
        self.business = self.tenants.business
        self.owner_id: UserId = self.tenants.owner_id
        self.staff_id: UserId = self.tenants.staff_id
        self.support: UserDocument = self.add_admin(SUPPORT_EMAIL, support_role)
        wall_clock = testbed.clock.build_wall_clock()
        authorize_admin = AuthorizePlatformAdminUseCase(
            testbed.user_repo, testbed.session_assurance, testbed.platform_admins
        )
        self.staff_alerts = RecordingStaffAlerts()
        self.open_cabinet = OpenClientCabinetUseCase(
            authorize_platform_admin=authorize_admin,
            platform_admins=testbed.platform_admins,
            business_repo=testbed.business_repo,
            grant_repo=testbed.grant_repo,
            audit_log_repo=testbed.audit_log_repo,
            staff_alerts=self.staff_alerts,
            localized_text_resolver=LocalizedTextResolver(),
            wall_clock=wall_clock,
            step_up=AllowStepUp(),
        )
        self.close_cabinet = CloseClientCabinetUseCase(
            authorize_admin, testbed.grant_repo, testbed.audit_log_repo, wall_clock
        )
        self.end_expired = EndExpiredSupportAccessUseCase(
            testbed.grant_repo, testbed.audit_log_repo, wall_clock
        )
        self.get_access = GetSupportAccessUseCase(
            testbed.authorize_business_access,
            testbed.grant_repo,
            testbed.user_repo,
            testbed.platform_admins,
            wall_clock,
        )
        self.update_write_access = UpdateSupportWriteAccessUseCase(
            testbed.authorize_business_access,
            testbed.grant_repo,
            testbed.audit_log_repo,
            testbed.user_repo,
            testbed.platform_admins,
            wall_clock,
            AllowStepUp(),
        )
        self.end_access = EndSupportAccessUseCase(
            testbed.authorize_business_access,
            testbed.grant_repo,
            testbed.audit_log_repo,
            wall_clock,
        )

    def add_admin(self, email: str, role: PlatformAdminRole) -> UserDocument:
        address = EmailAddress(email)
        admin = UserDocument(
            login_method=LoginMethod.EMAIL,
            email=address,
            locale=LanguageTag("en"),
            is_verified=True,
        )
        self.testbed.user_repo.save(admin)
        self.testbed.platform_admin_repo.save(
            PlatformAdminDocument(
                id=derive_platform_admin_id(LoginMethod.EMAIL, address),
                login_method=LoginMethod.EMAIL,
                email=address,
                role=role,
            )
        )
        return admin

    def as_support[T](
        self,
        work: Callable[[], T],
        mode: BusinessAccessMode = BusinessAccessMode.WRITE,
    ) -> T:
        return as_request(self.testbed.session_assurance, self.support.id, work, mode)

    def as_owner[T](self, work: Callable[[], T]) -> T:
        return as_request(self.testbed.session_assurance, self.owner_id, work)

    def open(self) -> ClientCabinetAccess:
        return self.as_support(
            lambda: self.open_cabinet.run(
                OpenClientCabinetCommand(
                    user_id=self.support.id,
                    business_id=self.business.id,
                    reason=REASON,
                    client_ip_address=ClientIpAddress(SUPPORT_IP),
                )
            )
        )

    def contact_command(self) -> ContactDataCommand:
        return ContactDataCommand(
            user_id=self.support.id,
            business_id=self.business.id,
            contact_id=self.tenants.visitor.contact.id,
            client_ip_address=ClientIpAddress(SUPPORT_IP),
        )
