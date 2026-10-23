"""
Rented phone numbers over the billing testbed: the phone line use cases,
the maintenance job and the monthly rental bills, wired over the same
in-memory storage, clock and notifier, with a fake carrier and voice
platform (`provisioner_fakes.py`). Nothing touches the network.
"""

from typed_time_provider import Microseconds

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.phone_numbers import PhoneLineLockRegistryContract
from app.registries.limits.request_rate_limit_registry import (
    RequestRateLimitRegistry,
)
from app.registries.locks.phone_line_lock_registry import PhoneLineLockRegistry
from app.registries.telephony.phone_number_country_registry import (
    PhoneNumberCountryRegistry,
)
from app.repositories.business_repositories import ChannelRepository
from app.repositories.phone_number_repositories import (
    PhoneNumberRepository,
    PhoneNumberRequestRepository,
)
from app.schemas.constants.assistants import AssistantToolName, AssistantVersionStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.phone_numbers import PhoneNumberType
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.phone_numbers import (
    PhoneNumberDocument,
    PhoneNumberRequestDocument,
)
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.phone_numbers.phone_line import (
    RentedPhoneNumberView,
    RentPhoneNumberCommand,
    RentPhoneNumberRequest,
)
from app.schemas.dto.phone_numbers.provisioning import PhoneNumberOfferClaims
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText, VoiceAgentId
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.telephony.constrained_strings import (
    PhoneNumberCityQuery,
    PhoneNumberOfferToken,
)
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
from app.use_cases.spend_guard.admit_owner_action_use_case import (
    AdmitOwnerActionUseCase,
    CheckOwnerActionRoomUseCase,
)
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from app.utilities.security.phone_number_offer_signer import PhoneNumberOfferSigner
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.billing.billing_testbed import BillingTestbed
from tests.billing.exchange_rate_fixtures import rate_registry
from tests.foundation.access_support import AllowStepUp
from tests.phone_numbers.phone_settings import phone_settings
from tests.phone_numbers.provisioner_fakes import FakePhoneNumberProvisioner

OFFER_KEY: PlatformSecret = PlatformSecret("test-key-0000")
OFFER_LIFETIME: int = 60 * 60 * 1_000_000
# 1.15 USD with 30 % at 2.7 GEL a dollar: 4.04 GEL, rounded up to 5 GEL.
USD_TO_GEL: str = "2.7"
AUSTIN_NUMBER: E164PhoneNumber = E164PhoneNumber("+15125550142")
FIVE_LARI: Money = Money(
    amount_minor=MoneyAmountMinor(500), currency_code=CurrencyCode("GEL")
)


class PhoneWorld(BillingTestbed):
    """Every billing use case plus the phone line's, over one storage."""

    def __init__(
        self,
        provisioner: FakePhoneNumberProvisioner | None = None,
        phone_line_lock: PhoneLineLockRegistryContract | None = None,
    ) -> None:
        super().__init__(
            exchange_rate_registry=rate_registry([("USD", "GEL", USD_TO_GEL)]),
            settings=phone_settings(),
        )
        wall_clock = self.clock.wall_clock
        self.provisioner = provisioner or FakePhoneNumberProvisioner()
        self.phone_number_repo = PhoneNumberRepository(
            InMemoryDocumentCollectionAdapter(PhoneNumberDocument)
        )
        self.request_repo = PhoneNumberRequestRepository(
            InMemoryDocumentCollectionAdapter(PhoneNumberRequestDocument)
        )
        self.channel_repo = ChannelRepository(
            InMemoryDocumentCollectionAdapter(ChannelDocument)
        )
        self.locks = InMemoryAdvisoryLockAdapter()
        self.phone_line_lock: PhoneLineLockRegistryContract = (
            phone_line_lock or PhoneLineLockRegistry(self.locks)
        )
        self.country_registry = PhoneNumberCountryRegistry()
        self.parser = PhoneNumberParser()
        self.offer_signer = PhoneNumberOfferSigner(OFFER_KEY)
        rate_limits = RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter())
        self.admit = AdmitOwnerActionUseCase(rate_limits, wall_clock)
        self.get_line = get_line.GetPhoneLineUseCase(
            self.authorize,
            self.phone_number_repo,
            self.request_repo,
            self.provisioner,
            self.country_registry,
            self.parser,
            self.assistant_version_repo,
        )
        self.search = search.SearchPhoneNumbersUseCase(
            self.authorize,
            self.provisioner,
            self.country_registry,
            self.exchange_rate_registry,
            self.parser,
            self.admit,
            self.settings,
            self.offer_signer,
            wall_clock,
        )
        self.rent = rent.RentPhoneNumberUseCase(
            authorize_business_access=self.authorize,
            step_up=AllowStepUp(),
            phone_number_repo=self.phone_number_repo,
            channel_repo=self.channel_repo,
            assistant_version_repo=self.assistant_version_repo,
            audit_log_repo=self.audit_log_repo,
            storage_scope=StorageScopeContext(),
            app_settings=self.settings,
            phone_number_provisioner=self.provisioner,
            phone_number_country_registry=self.country_registry,
            exchange_rate_registry=self.exchange_rate_registry,
            phone_number_parser=self.parser,
            phone_line_lock=self.phone_line_lock,
            check_owner_action_room=CheckOwnerActionRoomUseCase(
                rate_limits, wall_clock
            ),
            admit_owner_action=self.admit,
            product_events=self.product_events,
            offer_signer=self.offer_signer,
            wall_clock=wall_clock,
        )
        self.request_number = request_number.RequestPhoneNumberUseCase(
            self.authorize,
            self.request_repo,
            self.audit_log_repo,
            self.notifier,
            self.settings,
            self.admit,
            wall_clock,
        )
        self.cancel_request = cancel_request.CancelPhoneNumberRequestUseCase(
            self.authorize, self.request_repo, self.audit_log_repo, wall_clock
        )
        self.give_back = give_back.GiveBackPhoneNumberUseCase(
            self.phone_number_repo, self.phone_line_lock, wall_clock
        )
        self.maintain = maintain.MaintainPhoneNumbersUseCase(
            phone_number_repo=self.phone_number_repo,
            phone_number_request_repo=self.request_repo,
            business_repo=self.business_repo,
            channel_repo=self.channel_repo,
            assistant_version_repo=self.assistant_version_repo,
            phone_number_provisioner=self.provisioner,
            phone_line_lock=self.phone_line_lock,
            wall_clock=wall_clock,
        )
        self.bill_rentals = BillPhoneNumberRentalsUseCase(
            phone_number_repo=self.phone_number_repo,
            business_repo=self.business_repo,
            subscription_repo=self.subscription_repo,
            invoice_repo=self.invoice_repo,
            usage_event_repo=self.usage_event_repo,
            user_repo=self.user_repo,
            plan_registry=self.plan_registry,
            exchange_rate_registry=self.exchange_rate_registry,
            invoice_issuing=self.invoicing.invoice_issuing,
            invoice_description_transformer=self.invoice_description_transformer,
            invoice_line_texts_transformer=self.invoice_line_texts_transformer,
            manager_notifier=self.notifier,
            billing_notice_transformer=self.notice_transformer,
            phone_number_parser=self.parser,
            wall_clock=wall_clock,
        )

    def owner_and_business(
        self, email: str = "owner@example.com"
    ) -> tuple[UserDocument, BusinessDocument]:
        owner = self.add_user(email=email, locale="en", display_name="Nino")
        return owner, self.add_business(owner)

    def rent_austin_number(
        self,
        owner: UserDocument,
        business: BusinessDocument,
        phone_number: E164PhoneNumber = AUSTIN_NUMBER,
        price: Money = FIVE_LARI,
        number_type: PhoneNumberType = PhoneNumberType.LOCAL,
    ) -> RentedPhoneNumberView:
        return self.rent.run(
            RentPhoneNumberCommand(
                user_id=owner.id,
                business_id=business.id,
                request=RentPhoneNumberRequest(
                    phone_number=phone_number,
                    number_type=number_type,
                    offer_token=self.offer_token(business, phone_number, number_type),
                    monthly_price=price,
                    locality=PhoneNumberCityQuery("Austin"),
                ),
            )
        )

    def offer_token(
        self,
        business: BusinessDocument,
        phone_number: E164PhoneNumber,
        number_type: PhoneNumberType = PhoneNumberType.LOCAL,
    ) -> PhoneNumberOfferToken:
        """The token a search would have given, valid for an hour from now."""

        return self.offer_signer.sign(
            PhoneNumberOfferClaims(
                business_id=business.id,
                phone_number=phone_number,
                number_type=number_type,
                expires_at=Microseconds(self.clock.now() + OFFER_LIFETIME),
            )
        )

    def rented(self, business: BusinessDocument) -> PhoneNumberDocument:
        number = self.phone_number_repo.find_held(business.id)
        assert number is not None
        return number

    def publish_voice_agent(
        self, business: BusinessDocument, agent_id: str = "agent_0000"
    ) -> AssistantVersionDocument:
        version = AssistantVersionDocument(
            business_id=business.id,
            version_number=AssistantVersionNumber(1),
            status=AssistantVersionStatus.PUBLISHED,
            niche_key=NicheKey.ENTERTAINMENT,
            model_id=LlmModelId("gpt-5-mini"),
            prompt_text=SystemPromptText("You are the AI assistant."),
            tools=[AssistantToolName.CREATE_BOOKING],
            languages=[LanguageTag("ka")],
            default_language=LanguageTag("ka"),
            is_voice_enabled=True,
            facts=[],
            profile_revision=self.clock.now(),
            voice_agent_id=VoiceAgentId(agent_id),
        )
        self.assistant_version_repo.save(version)
        return version
