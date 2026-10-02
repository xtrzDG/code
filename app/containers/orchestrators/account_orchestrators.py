from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.assistant_use_cases import AssistantUseCasesContainer
from app.containers.use_cases.catalog_use_cases import CatalogUseCasesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.localization.call_forwarding_instructions_orchestrator import (
    CallForwardingInstructionsOrchestrator,
)
from app.schemas.dto.catalog import (
    CallForwardingInstructions,
    CallForwardingInstructionsRequest,
)


class AccountOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the catalog, sign-in and the current user,
    businesses and their teams.
    """

    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    catalog_use_cases: CatalogUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    assistant_use_cases: AssistantUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Call forwarding instructions (access check, then the instructions).
    call_forwarding_instructions_orchestrator: Factory[
        OrchestratorContract[
            CallForwardingInstructionsRequest,
            CallForwardingInstructions,
        ]
    ] = Factory(
        CallForwardingInstructionsOrchestrator,
        authorize_business_access_use_case=account_use_cases.authorize_business_access_use_case,
        build_call_forwarding_instructions_use_case=(
            catalog_use_cases.build_call_forwarding_instructions_use_case
        ),
    )

    # --- One use case per endpoint or job (typed through the use case).

    # --- Catalog.
    list_countries_orchestrator = use_case_orchestrator(
        catalog_use_cases.list_countries_use_case
    )
    get_country_profile_orchestrator = use_case_orchestrator(
        catalog_use_cases.get_country_profile_use_case
    )
    list_languages_orchestrator = use_case_orchestrator(
        catalog_use_cases.list_languages_use_case
    )
    quote_plans_orchestrator = use_case_orchestrator(
        catalog_use_cases.quote_plans_use_case
    )
    parse_phone_number_orchestrator = use_case_orchestrator(
        catalog_use_cases.parse_phone_number_use_case
    )

    # --- Sign-in and the current user.
    authenticate_user_orchestrator = use_case_orchestrator(
        account_use_cases.authenticate_user_use_case
    )
    start_otp_login_orchestrator = use_case_orchestrator(
        account_use_cases.start_otp_login_use_case
    )
    get_login_options_orchestrator = use_case_orchestrator(
        account_use_cases.get_login_options_use_case
    )
    verify_otp_login_orchestrator = use_case_orchestrator(
        account_use_cases.verify_otp_login_use_case
    )
    logout_orchestrator = use_case_orchestrator(account_use_cases.logout_use_case)
    get_current_user_orchestrator = use_case_orchestrator(
        account_use_cases.get_current_user_use_case
    )
    update_current_user_orchestrator = use_case_orchestrator(
        account_use_cases.update_current_user_use_case
    )

    # --- Businesses and teams.
    authorize_business_access_orchestrator = use_case_orchestrator(
        account_use_cases.authorize_business_access_use_case
    )
    create_business_orchestrator = use_case_orchestrator(
        account_use_cases.create_business_use_case
    )
    list_my_businesses_orchestrator = use_case_orchestrator(
        account_use_cases.list_my_businesses_use_case
    )
    get_business_orchestrator = use_case_orchestrator(
        account_use_cases.get_business_use_case
    )
    update_business_settings_orchestrator = use_case_orchestrator(
        assistant_use_cases.update_business_settings_use_case
    )
    invite_staff_orchestrator = use_case_orchestrator(
        account_use_cases.invite_staff_use_case
    )
    remove_member_orchestrator = use_case_orchestrator(
        account_use_cases.remove_member_use_case
    )
    change_member_role_orchestrator = use_case_orchestrator(
        account_use_cases.change_member_role_use_case
    )
