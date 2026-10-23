"""An owner takes a number for the business's phone line."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.phone_numbers import (
    PhoneLineLockRegistryContract,
    PhoneNumberCountryRegistryContract,
    PhoneNumberOfferSignerContract,
    PhoneNumberProvisionerAdapterContract,
    PhoneNumberRepoContract,
)
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.phone_numbers import PhoneNumberAvailability
from app.schemas.constants.spend import OwnerAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing import Money
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.dto.phone_numbers.phone_line import (
    RentedPhoneNumberView,
    RentPhoneNumberCommand,
)
from app.schemas.dto.phone_numbers.provisioning import (
    PhoneNumberPurchase,
    ProvisionedPhoneNumber,
)
from app.schemas.dto.spend_guard import OwnerActionAdmission
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.exceptions.phone_number_errors import PhoneNumberUnavailableError
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.telephony.constrained_strings import RentedLineNumber
from app.schemas.typings.telephony.strings import PhoneNumberLocality
from app.use_cases.channels.phone_numbers.phone_line_lookups import (
    find_answering_agent,
    quote_owner_price,
)
from app.use_cases.channels.phone_numbers.phone_line_records import PhoneLineRecords
from app.use_cases.channels.phone_numbers.phone_line_views import (
    build_rented_number_view,
)
from app.use_cases.channels.phone_numbers.rental_checks import (
    label_of,
    require_free_line,
    require_offered,
    require_quoted_price,
    require_unclaimed_number,
)
from app.use_cases.channels.phone_numbers.voice_attachment import attach_to_agent
from app.use_cases.shared.closure_guard import refuse_while_closing
from app.utilities.analytics.product_event_drafts import channel_connected_events
from app.utilities.telephony.rental_prices import as_rental_minor


class RentPhoneNumberUseCase(
    UseCaseContract[RentPhoneNumberCommand, RentedPhoneNumberView]
):
    """
    The owner (just signed in or confirmed: step-up) takes the number they
    picked from a search's offers (the offer's token vouches for the number
    and its kind: `require_offered`), at the monthly price the cabinet
    showed. Under the business's
    phone line lock (two clicks never rent two numbers): the business rents
    none yet and its phone channel carries no other number, nobody holds
    this one, its country is self-serve, and the carrier's price with the
    markup is still the price shown (else PhoneNumberPriceChangedError).
    A business takes at most three numbers a day (`owner_action_limits`;
    a purchase the carrier refuses is not counted).

    The number is rented, put on record at once (whatever fails later, the
    platform knows what it pays for), connected as the phone channel (calls
    find the business by it) and imported into the voice platform for the
    business's live voice agent; an import that fails is left to the
    maintenance job. The first rental month begins now (`billed_until`).
    Audited: the number and the channel. A closing business (a closure not
    cancelled) rents nothing: ConflictError, before the carrier is asked.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        step_up: StepUpGuardContract,
        phone_number_repo: PhoneNumberRepoContract,
        channel_repo: ChannelRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        audit_log_repo: AuditLogRepoContract,
        storage_scope: StorageScopeContract,
        app_settings: AppSettings,
        phone_number_provisioner: PhoneNumberProvisionerAdapterContract,
        phone_number_country_registry: PhoneNumberCountryRegistryContract,
        exchange_rate_registry: ExchangeRateRegistryContract,
        phone_number_parser: PhoneNumberParserContract,
        phone_line_lock: PhoneLineLockRegistryContract,
        check_owner_action_room: UseCaseContract[OwnerActionAdmission, None],
        admit_owner_action: UseCaseContract[OwnerActionAdmission, None],
        product_events: RecordProductEventFacilitatorContract,
        offer_signer: PhoneNumberOfferSignerContract,
        wall_clock: WallClock[Microseconds],
        closure_repo: BusinessClosureRepoContract | None = None,
    ) -> None:
        self._closure_repo: BusinessClosureRepoContract | None = closure_repo
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._step_up: StepUpGuardContract = step_up
        self._records: PhoneLineRecords = PhoneLineRecords(
            phone_number_repo,
            channel_repo,
            assistant_version_repo,
            audit_log_repo,
            storage_scope,
            app_settings,
        )
        self._provisioner: PhoneNumberProvisionerAdapterContract = (
            phone_number_provisioner
        )
        self._country_registry: PhoneNumberCountryRegistryContract = (
            phone_number_country_registry
        )
        self._exchange_rate_registry: ExchangeRateRegistryContract = (
            exchange_rate_registry
        )
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._phone_line_lock: PhoneLineLockRegistryContract = phone_line_lock
        self._check_owner_action_room: UseCaseContract[OwnerActionAdmission, None] = (
            check_owner_action_room
        )
        self._admit_owner_action: UseCaseContract[OwnerActionAdmission, None] = (
            admit_owner_action
        )
        self._product_events: RecordProductEventFacilitatorContract = product_events
        self._offer_signer: PhoneNumberOfferSignerContract = offer_signer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RentPhoneNumberCommand) -> RentedPhoneNumberView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        refuse_while_closing(self._closure_repo, business.id, "rent a number")
        # Renting costs money every month: only a recently proved person.
        self._step_up.require_recent_authentication()
        require_offered(
            self._offer_signer,
            business.id,
            input_data.request,
            self._wall_clock.now_unix(),
        )
        details: PhoneNumberDetails = self._phone_number_parser.parse(
            RawPhoneNumberInput(str(input_data.request.phone_number)), None
        )
        if (
            self._country_registry.get_availability(
                details.country_code, input_data.request.number_type
            )
            is not PhoneNumberAvailability.SELF_SERVE
        ):
            raise ConflictError(
                "Numbers of this kind in this country are arranged by the "
                "platform team: send a request instead."
            )

        if self._provisioner.list_missing_settings() != []:
            raise ConflictError(
                "This server does not rent numbers by itself: send a request "
                "and the platform team arranges one."
            )

        with self._phone_line_lock.lock_for(business.id):
            number: PhoneNumberDocument = self._rent(business, details, input_data)

        language = input_data.display_language or business.owner_language
        return build_rented_number_view(
            number,
            self._phone_number_parser,
            language,
            find_answering_agent(self._records.assistant_version_repo, business.id)
            is not None,
        )

    def _rent(
        self,
        business: BusinessDocument,
        details: PhoneNumberDetails,
        command: RentPhoneNumberCommand,
    ) -> PhoneNumberDocument:
        records: PhoneLineRecords = self._records
        require_free_line(
            records.phone_number_repo, records.channel_repo, business, details.e164
        )
        require_unclaimed_number(
            records.phone_number_repo,
            records.channel_repo,
            records.storage_scope,
            business,
            details.e164,
        )
        monthly_cost: CostMicroUsd | None = self._provisioner.quote_monthly_cost(
            details.country_code, command.request.number_type
        )
        if monthly_cost is None:
            raise PhoneNumberUnavailableError(
                "The carrier no longer sells this kind of number there."
            )

        price: Money = quote_owner_price(
            monthly_cost,
            records.app_settings.phone_numbers,
            business.currency_code,
            self._exchange_rate_registry,
        )
        require_quoted_price(price, command.request.monthly_price)
        admission = OwnerActionAdmission(
            action=OwnerAction.PHONE_NUMBER_RENTAL,
            user_id=command.user_id,
            business_id=business.id,
        )
        # Only numbers bought count (the carrier refusing one does not);
        # under the line lock nobody else counts for this business meanwhile.
        self._check_owner_action_room.run(admission)
        provisioned: ProvisionedPhoneNumber = self._provisioner.buy_number(
            PhoneNumberPurchase(phone_number=details.e164, label=label_of(business))
        )
        self._admit_owner_action.run(admission)
        now: Microseconds = self._wall_clock.now_unix()
        number = PhoneNumberDocument(
            business_id=business.id,
            provider=provisioned.provider,
            provider_number_id=provisioned.provider_number_id,
            # The number the carrier sold, as the business's line.
            phone_number=RentedLineNumber(str(provisioned.phone_number)),
            country_code=details.country_code,
            number_type=command.request.number_type,
            # The offer's city as the search showed it (display only).
            locality=(
                None
                if command.request.locality is None
                else PhoneNumberLocality(str(command.request.locality))
            ),
            monthly_price_minor=as_rental_minor(price),
            currency_code=price.currency_code,
            monthly_cost_micro_usd=monthly_cost,
            rented_by=command.user_id,
            rented_at=now,
            billed_until=now,
            created_at=now,
            updated_at=now,
        )
        records.phone_number_repo.save(number)
        records.record_rental(business.id, number, command, now)
        self._product_events.record(
            *channel_connected_events(command.user_id, business.id, ChannelKind.PHONE)
        )
        return attach_to_agent(
            self._provisioner,
            records.phone_number_repo,
            number,
            find_answering_agent(records.assistant_version_repo, business.id),
            label_of(business),
            now,
        )
