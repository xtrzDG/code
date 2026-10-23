from app.containers.phone_numbers.phone_number_dependencies import (
    PhoneNumberDependencies,
)
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


class PhoneNumberUseCaseFactories:
    """
    One typed factory per phone numbers use case (1213): the phone line in
    the cabinet (the rented number, numbers on offer, renting one, asking
    the team for one), giving a number back when the phone channel is
    turned off, and the two jobs (each rental month billed; numbers
    returned, kept with the live voice agent, requests closed). Each call
    builds a new use case from the context's dependencies.
    """

    def __init__(self, dependencies: PhoneNumberDependencies) -> None:
        self._dependencies: PhoneNumberDependencies = dependencies

    def get_phone_line(self) -> UseCaseContract[PhoneLineQuery, PhoneLineView]:
        given = self._dependencies
        return get_line.GetPhoneLineUseCase(
            authorize_business_access=given.authorize_business_access,
            phone_number_repo=given.phone_number_repo,
            phone_number_request_repo=given.phone_number_request_repo,
            phone_number_provisioner=given.phone_number_provisioner,
            phone_number_country_registry=given.phone_number_country_registry,
            phone_number_parser=given.phone_number_parser,
            assistant_version_repo=given.assistant_version_repo,
        )

    def search_phone_numbers(
        self,
    ) -> UseCaseContract[PhoneNumberOfferQuery, PhoneNumberOfferList]:
        given = self._dependencies
        return search.SearchPhoneNumbersUseCase(
            authorize_business_access=given.authorize_business_access,
            phone_number_provisioner=given.phone_number_provisioner,
            phone_number_country_registry=given.phone_number_country_registry,
            exchange_rate_registry=given.exchange_rate_registry,
            phone_number_parser=given.phone_number_parser,
            admit_owner_action=given.admit_owner_action,
            app_settings=given.app_settings,
            offer_signer=given.offer_signer,
            wall_clock=given.wall_clock,
        )

    def rent_phone_number(
        self,
    ) -> UseCaseContract[RentPhoneNumberCommand, RentedPhoneNumberView]:
        given = self._dependencies
        return rent.RentPhoneNumberUseCase(
            authorize_business_access=given.authorize_business_access,
            step_up=given.step_up,
            phone_number_repo=given.phone_number_repo,
            channel_repo=given.channel_repo,
            assistant_version_repo=given.assistant_version_repo,
            audit_log_repo=given.audit_log_repo,
            storage_scope=given.storage_scope,
            app_settings=given.app_settings,
            phone_number_provisioner=given.phone_number_provisioner,
            phone_number_country_registry=given.phone_number_country_registry,
            exchange_rate_registry=given.exchange_rate_registry,
            phone_number_parser=given.phone_number_parser,
            phone_line_lock=given.phone_line_lock,
            check_owner_action_room=given.check_owner_action_room,
            admit_owner_action=given.admit_owner_action,
            product_events=given.product_events,
            offer_signer=given.offer_signer,
            wall_clock=given.wall_clock,
            closure_repo=given.closure_repo,
        )

    def request_phone_number(
        self,
    ) -> UseCaseContract[RequestPhoneNumberCommand, PhoneNumberRequestView]:
        given = self._dependencies
        return request_number.RequestPhoneNumberUseCase(
            authorize_business_access=given.authorize_business_access,
            phone_number_request_repo=given.phone_number_request_repo,
            audit_log_repo=given.audit_log_repo,
            manager_notifier=given.manager_notifier,
            app_settings=given.app_settings,
            admit_owner_action=given.admit_owner_action,
            wall_clock=given.wall_clock,
        )

    def cancel_phone_number_request(
        self,
    ) -> UseCaseContract[CancelPhoneNumberRequestCommand, None]:
        given = self._dependencies
        return cancel_request.CancelPhoneNumberRequestUseCase(
            authorize_business_access=given.authorize_business_access,
            phone_number_request_repo=given.phone_number_request_repo,
            audit_log_repo=given.audit_log_repo,
            wall_clock=given.wall_clock,
        )

    def give_back_phone_number(self) -> UseCaseContract[BusinessId, None]:
        """Run by turning the phone channel off (DisableChannelUseCase)."""

        given = self._dependencies
        return give_back.GiveBackPhoneNumberUseCase(
            phone_number_repo=given.phone_number_repo,
            phone_line_lock=given.phone_line_lock,
            wall_clock=given.wall_clock,
        )

    def maintain_phone_numbers(self) -> UseCaseContract[JobTick, JobReport]:
        given = self._dependencies
        return maintain.MaintainPhoneNumbersUseCase(
            phone_number_repo=given.phone_number_repo,
            phone_number_request_repo=given.phone_number_request_repo,
            business_repo=given.business_repo,
            channel_repo=given.channel_repo,
            assistant_version_repo=given.assistant_version_repo,
            phone_number_provisioner=given.phone_number_provisioner,
            phone_line_lock=given.phone_line_lock,
            wall_clock=given.wall_clock,
        )

    def bill_phone_number_rentals(self) -> UseCaseContract[JobTick, JobReport]:
        given = self._dependencies
        return BillPhoneNumberRentalsUseCase(
            phone_number_repo=given.phone_number_repo,
            business_repo=given.business_repo,
            subscription_repo=given.subscription_repo,
            invoice_repo=given.invoice_repo,
            usage_event_repo=given.usage_event_repo,
            user_repo=given.user_repo,
            plan_registry=given.plan_registry,
            exchange_rate_registry=given.exchange_rate_registry,
            invoice_issuing=given.invoice_issuing,
            invoice_description_transformer=given.invoice_description_transformer,
            invoice_line_texts_transformer=given.invoice_line_texts_transformer,
            manager_notifier=given.manager_notifier,
            billing_notice_transformer=given.billing_notice_transformer,
            phone_number_parser=given.phone_number_parser,
            wall_clock=given.wall_clock,
        )
