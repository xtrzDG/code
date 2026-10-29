from dependency_injector.providers import Factory, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.phone_numbers.phone_number_dependencies import (
    PhoneNumberDependencies,
)
from app.containers.phone_numbers.phone_number_root import PhoneNumberRoot
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.spend_guard_use_cases import (
    admit_owner_action_factory,
    check_owner_action_room_factory,
)
from app.containers.utilities import UtilitiesContainer


def phone_number_root_provider(
    *,
    adapters: AdaptersContainer,
    config: ConfigContainer,
    facilitators: FacilitatorsContainer,
    registries: RegistriesContainer,
    repositories: RepositoriesContainer,
    time_provider: TimeProviderContainer,
    transformers: TransformersContainer,
    utilities: UtilitiesContainer,
    account_use_cases: AccountUseCasesContainer,
) -> Singleton[PhoneNumberRoot]:
    """
    The phone numbers context's one root (W21-PHONE-NUMBERS, migration
    1213), its dependencies taken from the graph: the single seam between
    the providers and the typed root (app/containers/phone_numbers/, ADR
    0010; a missing or misspelt field fails
    test_every_provider_of_the_container_resolves).
    """

    return Singleton(
        PhoneNumberRoot,
        dependencies=Factory(
            PhoneNumberDependencies,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            admit_owner_action=admit_owner_action_factory(registries, time_provider),
            check_owner_action_room=check_owner_action_room_factory(
                registries, time_provider
            ),
            step_up=utilities.step_up_guard,
            phone_number_repo=repositories.phone_number_repo,
            phone_number_request_repo=repositories.phone_number_request_repo,
            channel_repo=repositories.channel_repo,
            closure_repo=repositories.business_closure_repo,
            assistant_version_repo=repositories.assistant_version_repo,
            audit_log_repo=repositories.audit_log_repo,
            business_repo=repositories.business_repo,
            subscription_repo=repositories.subscription_repo,
            invoice_repo=repositories.invoice_repo,
            usage_event_repo=repositories.usage_event_repo,
            user_repo=repositories.user_repo,
            phone_number_provisioner=adapters.phone_number_provisioner,
            phone_number_country_registry=registries.phone_number_country_registry,
            exchange_rate_registry=registries.exchange_rate_registry,
            plan_registry=registries.plan_registry,
            phone_line_lock=registries.phone_line_lock_registry,
            phone_number_parser=utilities.phone_number_parser,
            offer_signer=utilities.phone_number_offer_signer,
            invoice_issuing=facilitators.invoice_issuing_facilitator,
            manager_notifier=facilitators.manager_notification_facilitator,
            product_events=facilitators.product_events,
            invoice_description_transformer=transformers.invoice_description_transformer,
            invoice_line_texts_transformer=transformers.invoice_line_texts_transformer,
            billing_notice_transformer=transformers.billing_notice_transformer,
            storage_scope=utilities.storage_scope,
            app_settings=config.app_settings,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
    )
