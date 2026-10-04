from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.businesses import (
    BusinessQuery,
    BusinessView,
    ChangeMemberRoleCommand,
    CreateBusinessCommand,
    InviteStaffCommand,
    RemoveMemberCommand,
)
from app.schemas.dto.login_options import LoginOptionsQuery, LoginOptionsView
from app.schemas.dto.login_protection import SendLoginCodeCommand
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.users import (
    CurrentUserView,
    LoginSessionView,
    LogoutCommand,
    OtpChallengeView,
    StartOtpLoginCommand,
    UpdateCurrentUserCommand,
    UserView,
    VerifyOtpLoginCommand,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.businesses.change_member_role_use_case import ChangeMemberRoleUseCase
from app.use_cases.businesses.create_business_use_case import CreateBusinessUseCase
from app.use_cases.businesses.get_business_use_case import GetBusinessUseCase
from app.use_cases.businesses.invite_staff_use_case import InviteStaffUseCase
from app.use_cases.businesses.list_my_businesses_use_case import ListMyBusinessesUseCase
from app.use_cases.businesses.remove_member_use_case import RemoveMemberUseCase
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


class AccountUseCasesContainer(containers.DeclarativeContainer):
    """
    Access to a business, sign-in and the current user, businesses and their
    teams. Every cabinet use case checks access with
    `authorize_business_access_use_case` first.
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Access to a business (owners, staff, audited platform admins).
    authorize_business_access_use_case: Factory[
        UseCaseContract[BusinessAccessRequest, BusinessDocument]
    ] = Factory(
        AuthorizeBusinessAccessUseCase,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        session_assurance=utilities.session_assurance,
        app_settings=config.app_settings,
    )

    # --- Sign-in and the current user.
    send_login_code_use_case: Factory[
        UseCaseContract[SendLoginCodeCommand, OtpChallengeDocument]
    ] = Factory(
        SendLoginCodeUseCase,
        otp_challenge_repo=repositories.otp_challenge_repo,
        otp_delivery_facilitator=facilitators.otp_delivery_facilitator,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        send_lock_registry=registries.login_code_send_lock_registry,
        bot_check=facilitators.bot_check_facilitator,
        cap_alerts=facilitators.login_code_cap_alerts,
    )
    start_otp_login_use_case: Factory[
        UseCaseContract[StartOtpLoginCommand, OtpChallengeView]
    ] = Factory(
        StartOtpLoginUseCase,
        phone_number_parser=utilities.phone_number_parser,
        country_registry=registries.country_registry,
        language_registry=registries.language_registry,
        otp_delivery_facilitator=facilitators.otp_delivery_facilitator,
        app_settings=config.app_settings,
        user_repo=repositories.user_repo,
        high_cost_phone_registry=registries.high_cost_phone_number_registry,
        send_login_code=send_login_code_use_case,
    )
    get_login_options_use_case: Factory[
        UseCaseContract[LoginOptionsQuery, LoginOptionsView]
    ] = Factory(
        GetLoginOptionsUseCase,
        country_registry=registries.country_registry,
        otp_delivery_facilitator=facilitators.otp_delivery_facilitator,
        app_settings=config.app_settings,
    )
    verify_otp_login_use_case: Factory[
        UseCaseContract[VerifyOtpLoginCommand, LoginSessionView]
    ] = Factory(
        VerifyOtpLoginUseCase,
        otp_challenge_repo=repositories.otp_challenge_repo,
        user_repo=repositories.user_repo,
        user_session_repo=repositories.user_session_repo,
        audit_log_repo=repositories.audit_log_repo,
        user_view_transformer=transformers.user_view_transformer,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        rate_limit_registry=registries.request_rate_limit_registry,
        product_events=facilitators.product_events,
        totp_factor_repo=repositories.totp_factor_repo,
        mfa_challenge_repo=repositories.mfa_challenge_repo,
    )
    authenticate_user_use_case: Factory[
        UseCaseContract[AccessToken, SessionAssurance]
    ] = Factory(
        AuthenticateUserUseCase,
        user_session_repo=repositories.user_session_repo,
        user_repo=repositories.user_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    logout_use_case: Factory[UseCaseContract[LogoutCommand, None]] = Factory(
        LogoutUseCase,
        user_session_repo=repositories.user_session_repo,
    )
    get_current_user_use_case: Factory[UseCaseContract[UserId, CurrentUserView]] = (
        Factory(
            GetCurrentUserUseCase,
            user_repo=repositories.user_repo,
            business_repo=repositories.business_repo,
            user_view_transformer=transformers.user_view_transformer,
            session_assurance=utilities.session_assurance,
            app_settings=config.app_settings,
        )
    )
    update_current_user_use_case: Factory[
        UseCaseContract[UpdateCurrentUserCommand, UserView]
    ] = Factory(
        UpdateCurrentUserUseCase,
        user_repo=repositories.user_repo,
        language_registry=registries.language_registry,
        user_view_transformer=transformers.user_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Businesses and teams.
    create_business_use_case: Factory[
        UseCaseContract[CreateBusinessCommand, BusinessView]
    ] = Factory(
        CreateBusinessUseCase,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        country_registry=registries.country_registry,
        language_registry=registries.language_registry,
        niche_template_registry=registries.niche_template_registry,
        business_view_transformer=transformers.business_view_transformer,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        product_events=facilitators.product_events,
    )
    list_my_businesses_use_case: Factory[
        UseCaseContract[UserId, list[BusinessView]]
    ] = Factory(
        ListMyBusinessesUseCase,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        business_view_transformer=transformers.business_view_transformer,
    )
    get_business_use_case: Factory[UseCaseContract[BusinessQuery, BusinessView]] = (
        Factory(
            GetBusinessUseCase,
            authorize_business_access=authorize_business_access_use_case,
            user_repo=repositories.user_repo,
            business_view_transformer=transformers.business_view_transformer,
        )
    )
    invite_staff_use_case: Factory[
        UseCaseContract[InviteStaffCommand, BusinessView]
    ] = Factory(
        InviteStaffUseCase,
        authorize_business_access=authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        phone_number_parser=utilities.phone_number_parser,
        audit_log_repo=repositories.audit_log_repo,
        business_view_transformer=transformers.business_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
        step_up=utilities.step_up_guard,
    )
    change_member_role_use_case: Factory[
        UseCaseContract[ChangeMemberRoleCommand, BusinessView]
    ] = Factory(
        ChangeMemberRoleUseCase,
        authorize_business_access=authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        audit_log_repo=repositories.audit_log_repo,
        business_view_transformer=transformers.business_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
        step_up=utilities.step_up_guard,
    )
    remove_member_use_case: Factory[
        UseCaseContract[RemoveMemberCommand, BusinessView]
    ] = Factory(
        RemoveMemberUseCase,
        authorize_business_access=authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        user_repo=repositories.user_repo,
        audit_log_repo=repositories.audit_log_repo,
        business_view_transformer=transformers.business_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
        step_up=utilities.step_up_guard,
    )
