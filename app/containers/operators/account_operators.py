from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.account_pipelines import AccountPipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class AccountOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the catalog, sign-in and the current user, businesses
    and their teams.
    """

    account_pipelines: AccountPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve.
    storage_scope = utilities.storage_scope

    # --- Dedicated orchestrator: access check, then the instructions.
    call_forwarding_instructions_operator = pipeline_operator(
        account_pipelines.call_forwarding_instructions_pipeline, storage_scope
    )

    # --- One use case per endpoint or job.

    # --- Catalog.
    list_countries_operator = pipeline_operator(
        account_pipelines.list_countries_pipeline, storage_scope
    )
    get_country_profile_operator = pipeline_operator(
        account_pipelines.get_country_profile_pipeline, storage_scope
    )
    list_languages_operator = pipeline_operator(
        account_pipelines.list_languages_pipeline, storage_scope
    )
    quote_plans_operator = pipeline_operator(
        account_pipelines.quote_plans_pipeline, storage_scope
    )
    parse_phone_number_operator = pipeline_operator(
        account_pipelines.parse_phone_number_pipeline, storage_scope
    )

    # --- Sign-in and the current user.
    authenticate_user_operator = pipeline_operator(
        account_pipelines.authenticate_user_pipeline, storage_scope
    )
    start_otp_login_operator = pipeline_operator(
        account_pipelines.start_otp_login_pipeline, storage_scope
    )
    get_login_options_operator = pipeline_operator(
        account_pipelines.get_login_options_pipeline, storage_scope
    )
    verify_otp_login_operator = pipeline_operator(
        account_pipelines.verify_otp_login_pipeline, storage_scope
    )
    logout_operator = pipeline_operator(
        account_pipelines.logout_pipeline, storage_scope
    )
    get_current_user_operator = pipeline_operator(
        account_pipelines.get_current_user_pipeline, storage_scope
    )
    update_current_user_operator = pipeline_operator(
        account_pipelines.update_current_user_pipeline, storage_scope
    )

    # --- Businesses and teams.
    authorize_business_access_operator = pipeline_operator(
        account_pipelines.authorize_business_access_pipeline, storage_scope
    )
    create_business_operator = pipeline_operator(
        account_pipelines.create_business_pipeline, storage_scope
    )
    list_my_businesses_operator = pipeline_operator(
        account_pipelines.list_my_businesses_pipeline, storage_scope
    )
    get_business_operator = pipeline_operator(
        account_pipelines.get_business_pipeline, storage_scope
    )
    update_business_settings_operator = pipeline_operator(
        account_pipelines.update_business_settings_pipeline, storage_scope
    )
    invite_staff_operator = pipeline_operator(
        account_pipelines.invite_staff_pipeline, storage_scope
    )
    remove_member_operator = pipeline_operator(
        account_pipelines.remove_member_pipeline, storage_scope
    )
    change_member_role_operator = pipeline_operator(
        account_pipelines.change_member_role_pipeline, storage_scope
    )
