from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
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
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.phone_numbers.phone_line import (
    CancelPhoneNumberRequestCommand,
    PhoneLineQuery,
    PhoneLineView,
    PhoneNumberOfferList,
    PhoneNumberOfferQuery,
    PhoneNumberRequestView,
    RentedPhoneNumberView,
    RentPhoneNumberCommand,
    RequestPhoneNumberCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.billing.number_rentals.bill_phone_number_rentals_use_case import (
    BillPhoneNumberRentalsUseCase,
)
from app.use_cases.channels.phone_numbers import (
    cancel_phone_number_request_use_case as cancel_request,
)
from app.use_cases.channels.phone_numbers import (
    get_phone_line_use_case as get_line,
)
from app.use_cases.channels.phone_numbers import (
    give_back_phone_number_use_case as give_back,
)
from app.use_cases.channels.phone_numbers import (
    maintain_phone_numbers_use_case as maintain,
)
from app.use_cases.channels.phone_numbers import (
    rent_phone_number_use_case as rent,
)
from app.use_cases.channels.phone_numbers import (
    request_phone_number_use_case as request_number,
)
from app.use_cases.channels.phone_numbers import (
    search_phone_numbers_use_case as search,
)


class PhoneNumberUseCasesContainer(containers.DeclarativeContainer):
    """
    Phone numbers the platform rents for businesses (1213): the phone line
    in the cabinet (the rented number, numbers on offer, renting one,
    asking the team for one), giving a number back when the phone channel
    is turned off, and the two jobs (each rental month billed; numbers
    returned, kept with the live voice agent, requests closed).
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_phone_line_use_case: Factory[UseCaseContract[PhoneLineQuery, PhoneLineView]] = (
        Factory(
            get_line.GetPhoneLineUseCase,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            phone_number_repo=repositories.phone_number_repo,
            phone_number_request_repo=repositories.phone_number_request_repo,
            phone_number_provisioner=adapters.calls.phone_number_provisioner,
            phone_number_country_registry=registries.phone_number_country_registry,
            phone_number_parser=utilities.phone_number_parser,
            assistant_version_repo=repositories.assistant_version_repo,
        )
    )
    search_phone_numbers_use_case: Factory[
        UseCaseContract[PhoneNumberOfferQuery, PhoneNumberOfferList]
    ] = Factory(
        search.SearchPhoneNumbersUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        phone_number_provisioner=adapters.calls.phone_number_provisioner,
        phone_number_country_registry=registries.phone_number_country_registry,
        exchange_rate_registry=registries.exchange_rate_registry,
        phone_number_parser=utilities.phone_number_parser,
        admit_owner_action=admit_owner_action_factory(registries, time_provider),
        app_settings=config.app_settings,
        offer_signer=utilities.phone_number_offer_signer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    rent_phone_number_use_case: Factory[
        UseCaseContract[RentPhoneNumberCommand, RentedPhoneNumberView]
    ] = Factory(
        rent.RentPhoneNumberUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        step_up=utilities.step_up_guard,
        phone_number_repo=repositories.phone_number_repo,
        channel_repo=repositories.channel_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        audit_log_repo=repositories.audit_log_repo,
        storage_scope=utilities.storage_scope,
        app_settings=config.app_settings,
        phone_number_provisioner=adapters.calls.phone_number_provisioner,
        phone_number_country_registry=registries.phone_number_country_registry,
        exchange_rate_registry=registries.exchange_rate_registry,
        phone_number_parser=utilities.phone_number_parser,
        phone_line_lock=registries.phone_line_lock_registry,
        check_owner_action_room=check_owner_action_room_factory(
            registries, time_provider
        ),
        admit_owner_action=admit_owner_action_factory(registries, time_provider),
        product_events=facilitators.product_events,
        offer_signer=utilities.phone_number_offer_signer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    request_phone_number_use_case: Factory[
        UseCaseContract[RequestPhoneNumberCommand, PhoneNumberRequestView]
    ] = Factory(
        request_number.RequestPhoneNumberUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        phone_number_request_repo=repositories.phone_number_request_repo,
        audit_log_repo=repositories.audit_log_repo,
        manager_notifier=facilitators.manager_notification_facilitator,
        app_settings=config.app_settings,
        admit_owner_action=admit_owner_action_factory(registries, time_provider),
        wall_clock=time_provider.microsecond_wall_clock,
    )
    cancel_phone_number_request_use_case: Factory[
        UseCaseContract[CancelPhoneNumberRequestCommand, None]
    ] = Factory(
        cancel_request.CancelPhoneNumberRequestUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        phone_number_request_repo=repositories.phone_number_request_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # Run by turning the phone channel off (DisableChannelUseCase).
    give_back_phone_number_use_case: Factory[UseCaseContract[BusinessId, None]] = (
        Factory(
            give_back.GiveBackPhoneNumberUseCase,
            phone_number_repo=repositories.phone_number_repo,
            phone_line_lock=registries.phone_line_lock_registry,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    # Periodic jobs over every business.
    maintain_phone_numbers_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            maintain.MaintainPhoneNumbersUseCase,
            phone_number_repo=repositories.phone_number_repo,
            phone_number_request_repo=repositories.phone_number_request_repo,
            business_repo=repositories.business_repo,
            channel_repo=repositories.channel_repo,
            assistant_version_repo=repositories.assistant_version_repo,
            phone_number_provisioner=adapters.calls.phone_number_provisioner,
            phone_line_lock=registries.phone_line_lock_registry,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    bill_phone_number_rentals_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            BillPhoneNumberRentalsUseCase,
            phone_number_repo=repositories.phone_number_repo,
            business_repo=repositories.business_repo,
            subscription_repo=repositories.subscription_repo,
            invoice_repo=repositories.invoice_repo,
            usage_event_repo=repositories.usage_event_repo,
            user_repo=repositories.user_repo,
            plan_registry=registries.plan_registry,
            exchange_rate_registry=registries.exchange_rate_registry,
            invoice_issuing=facilitators.invoice_issuing_facilitator,
            invoice_description_transformer=transformers.invoice_description_transformer,
            invoice_line_texts_transformer=transformers.invoice_line_texts_transformer,
            manager_notifier=facilitators.manager_notification_facilitator,
            billing_notice_transformer=transformers.billing_notice_transformer,
            phone_number_parser=utilities.phone_number_parser,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
