"""The accounts testbed's sign-in, profile and business use cases, wired."""

from collections.abc import Mapping

from typed_time_provider import Microseconds, WallClock

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.registries.localization.high_cost_phone_number_registry import (
    HighCostPhoneNumberRegistry,
)
from app.registries.locks.login_code_send_lock_registry import LoginCodeSendLockRegistry
from app.transformers.businesses.business_view_transformer import (
    BusinessViewTransformer,
)
from app.transformers.users.user_view_transformer import UserViewTransformer
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.businesses.change_member_role_use_case import ChangeMemberRoleUseCase
from app.use_cases.businesses.create_business_use_case import CreateBusinessUseCase
from app.use_cases.businesses.get_business_use_case import GetBusinessUseCase
from app.use_cases.businesses.invite_staff_use_case import InviteStaffUseCase
from app.use_cases.businesses.list_my_businesses_use_case import ListMyBusinessesUseCase
from app.use_cases.businesses.remove_member_use_case import RemoveMemberUseCase
from app.use_cases.businesses.update_business_settings_use_case import (
    UpdateBusinessSettingsUseCase,
)
from app.use_cases.users.authenticate_user_use_case import AuthenticateUserUseCase
from app.use_cases.users.get_current_user_use_case import GetCurrentUserUseCase
from app.use_cases.users.get_login_options_use_case import GetLoginOptionsUseCase
from app.use_cases.users.logout_use_case import LogoutUseCase
from app.use_cases.users.otp_login.send_login_code_use_case import (
    SendLoginCodeUseCase,
)
from app.use_cases.users.otp_login.start_otp_login_use_case import StartOtpLoginUseCase
from app.use_cases.users.update_current_user_use_case import UpdateCurrentUserUseCase
from app.use_cases.users.verify_otp_login_use_case import VerifyOtpLoginUseCase
from tests.users.accounts_recorders import (
    RecordingAssistantResumption,
    RecordingVoiceAgentRemoval,
)
from tests.users.accounts_repositories import AccountsRepositories
from tests.users.login_protection_fakes import FakeBotCheck, RecordingCapAlerts


class AccountsUserUseCases(AccountsRepositories):
    """Login, current user, business and team use cases over the repositories."""

    def __init__(self, environment_variables: Mapping[str, str]) -> None:
        super().__init__(environment_variables)
        wall_clock: WallClock[Microseconds] = self.clock.build_wall_clock()

        user_view_transformer = UserViewTransformer()
        business_view_transformer = BusinessViewTransformer()
        self.authorize_business_access = AuthorizeBusinessAccessUseCase(
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )

        self.login_rate_limits = RequestRateLimitRegistry(
            InMemoryRateLimitBucketAdapter()
        )
        self.bot_check = FakeBotCheck()
        self.cap_alerts = RecordingCapAlerts()
        self.send_login_code = SendLoginCodeUseCase(
            otp_challenge_repo=self.otp_challenge_repo,
            otp_delivery_facilitator=self.otp_delivery,
            app_settings=self.settings,
            wall_clock=wall_clock,
            send_lock_registry=LoginCodeSendLockRegistry(InMemoryAdvisoryLockAdapter()),
            bot_check=self.bot_check,
            cap_alerts=self.cap_alerts,
        )
        self.start_otp_login = StartOtpLoginUseCase(
            phone_number_parser=self.phone_parser,
            country_registry=self.country_registry,
            language_registry=self.language_registry,
            otp_delivery_facilitator=self.otp_delivery,
            app_settings=self.settings,
            user_repo=self.user_repo,
            high_cost_phone_registry=HighCostPhoneNumberRegistry(
                self.settings.otp_denied_phone_prefixes
            ),
            send_login_code=self.send_login_code,
        )
        self.get_login_options = GetLoginOptionsUseCase(
            country_registry=self.country_registry,
            otp_delivery_facilitator=self.otp_delivery,
            app_settings=self.settings,
        )
        self.verify_otp_login = VerifyOtpLoginUseCase(
            otp_challenge_repo=self.otp_challenge_repo,
            user_repo=self.user_repo,
            user_session_repo=self.user_session_repo,
            audit_log_repo=self.audit_log_repo,
            user_view_transformer=user_view_transformer,
            app_settings=self.settings,
            wall_clock=wall_clock,
            rate_limit_registry=self.login_rate_limits,
        )
        self.authenticate_user = AuthenticateUserUseCase(
            user_session_repo=self.user_session_repo,
            user_repo=self.user_repo,
            wall_clock=wall_clock,
        )
        self.logout = LogoutUseCase(user_session_repo=self.user_session_repo)
        self.get_current_user = GetCurrentUserUseCase(
            user_repo=self.user_repo,
            business_repo=self.business_repo,
            user_view_transformer=user_view_transformer,
        )
        self.update_current_user = UpdateCurrentUserUseCase(
            user_repo=self.user_repo,
            language_registry=self.language_registry,
            user_view_transformer=user_view_transformer,
            wall_clock=wall_clock,
        )

        self.create_business = CreateBusinessUseCase(
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            country_registry=self.country_registry,
            language_registry=self.language_registry,
            niche_template_registry=self.niche_registry,
            business_view_transformer=business_view_transformer,
            app_settings=self.settings,
            wall_clock=wall_clock,
        )
        self.list_my_businesses = ListMyBusinessesUseCase(
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            business_view_transformer=business_view_transformer,
        )
        self.get_business = GetBusinessUseCase(
            authorize_business_access=self.authorize_business_access,
            user_repo=self.user_repo,
            business_view_transformer=business_view_transformer,
        )
        self.voice_agent_removals = RecordingVoiceAgentRemoval()
        self.assistant_resumptions = RecordingAssistantResumption()
        self.update_business_settings = UpdateBusinessSettingsUseCase(
            authorize_business_access=self.authorize_business_access,
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            subscription_repo=self.subscription_repo,
            language_registry=self.language_registry,
            phone_number_parser=self.phone_parser,
            audit_log_repo=self.audit_log_repo,
            business_view_transformer=business_view_transformer,
            wall_clock=wall_clock,
            remove_voice_agent=self.voice_agent_removals,
            resume_assistant=self.assistant_resumptions,
        )
        self.invite_staff = InviteStaffUseCase(
            authorize_business_access=self.authorize_business_access,
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            phone_number_parser=self.phone_parser,
            audit_log_repo=self.audit_log_repo,
            business_view_transformer=business_view_transformer,
            wall_clock=wall_clock,
        )
        self.remove_member = RemoveMemberUseCase(
            authorize_business_access=self.authorize_business_access,
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_log_repo,
            business_view_transformer=business_view_transformer,
            wall_clock=wall_clock,
        )
        self.change_member_role = ChangeMemberRoleUseCase(
            authorize_business_access=self.authorize_business_access,
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_log_repo,
            business_view_transformer=business_view_transformer,
            wall_clock=wall_clock,
        )
