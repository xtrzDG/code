from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.account_orchestrators import (
    AccountOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class AccountPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of the catalog, sign-in and the current user, businesses
    and their teams.
    """

    account_orchestrators: AccountOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Dedicated orchestrators.
    call_forwarding_instructions_pipeline = orchestrator_pipeline(
        account_orchestrators.call_forwarding_instructions_orchestrator
    )

    # --- One orchestrator per endpoint or job.

    # --- Catalog.
    list_countries_pipeline = orchestrator_pipeline(
        account_orchestrators.list_countries_orchestrator
    )
    get_country_profile_pipeline = orchestrator_pipeline(
        account_orchestrators.get_country_profile_orchestrator
    )
    list_languages_pipeline = orchestrator_pipeline(
        account_orchestrators.list_languages_orchestrator
    )
    quote_plans_pipeline = orchestrator_pipeline(
        account_orchestrators.quote_plans_orchestrator
    )
    parse_phone_number_pipeline = orchestrator_pipeline(
        account_orchestrators.parse_phone_number_orchestrator
    )

    # --- Sign-in and the current user.
    authenticate_user_pipeline = orchestrator_pipeline(
        account_orchestrators.authenticate_user_orchestrator
    )
    start_otp_login_pipeline = orchestrator_pipeline(
        account_orchestrators.start_otp_login_orchestrator
    )
    get_login_options_pipeline = orchestrator_pipeline(
        account_orchestrators.get_login_options_orchestrator
    )
    verify_otp_login_pipeline = orchestrator_pipeline(
        account_orchestrators.verify_otp_login_orchestrator
    )
    logout_pipeline = orchestrator_pipeline(account_orchestrators.logout_orchestrator)
    get_current_user_pipeline = orchestrator_pipeline(
        account_orchestrators.get_current_user_orchestrator
    )
    update_current_user_pipeline = orchestrator_pipeline(
        account_orchestrators.update_current_user_orchestrator
    )

    # --- Businesses and teams.
    authorize_business_access_pipeline = orchestrator_pipeline(
        account_orchestrators.authorize_business_access_orchestrator
    )
    create_business_pipeline = orchestrator_pipeline(
        account_orchestrators.create_business_orchestrator
    )
    list_my_businesses_pipeline = orchestrator_pipeline(
        account_orchestrators.list_my_businesses_orchestrator
    )
    get_business_pipeline = orchestrator_pipeline(
        account_orchestrators.get_business_orchestrator
    )
    update_business_settings_pipeline = orchestrator_pipeline(
        account_orchestrators.update_business_settings_orchestrator
    )
    invite_staff_pipeline = orchestrator_pipeline(
        account_orchestrators.invite_staff_orchestrator
    )
    remove_member_pipeline = orchestrator_pipeline(
        account_orchestrators.remove_member_orchestrator
    )
    change_member_role_pipeline = orchestrator_pipeline(
        account_orchestrators.change_member_role_orchestrator
    )
