"""Fakes and an in-memory wiring of the accounts slice, shared by its tests.

Countries, languages and niches come from small fake registries; phone
numbers are parsed with the real `phonenumbers` library. Time is an
adjustable clock so expiry and retention can be tested without sleeping.
"""

from collections.abc import Mapping
from dataclasses import dataclass

import phonenumbers
from fastapi import FastAPI
from fastapi.testclient import TestClient
from phonenumbers import NumberParseException, PhoneNumberFormat, PhoneNumberType
from phonenumbers import timezone as phone_timezones
from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.registries import (
    CountryRegistryContract,
    LanguageRegistryContract,
    NicheTemplateRegistryContract,
)
from app.gateways.http.business_routes import build_business_router
from app.gateways.http.compliance_routes import build_compliance_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.gateways.http.users_routes import build_users_router
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.repositories.billing_repositories import SubscriptionRepository
from app.repositories.booking_repositories import (
    BookingRepository,
    HandoffRepository,
    LeadRepository,
)
from app.repositories.business_repositories import BusinessRepository
from app.repositories.compliance_repositories import (
    AuditLogRepository,
    DpaAcceptanceRepository,
)
from app.repositories.conversation_repositories import (
    CallRepository,
    ContactRepository,
    ConversationRepository,
    LlmTurnRepository,
    MessageRepository,
)
from app.repositories.user_repositories import (
    OtpChallengeRepository,
    UserRepository,
    UserSessionRepository,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    DataRegion,
    LanguageTextSupport,
    LanguageVoiceSupport,
    LocalNumberProvisioning,
    OtpDeliveryChannel,
    PhoneNumberKind,
    RecordingConsentRule,
    TextDirection,
)
from app.schemas.constants.niches import LaunchWave, NicheKey
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.dto.businesses import CreateBusinessCommand, CreateBusinessRequest
from app.schemas.dto.localization import (
    CountryProfile,
    LanguageProfile,
    LocalizedText,
    PhoneNumberDetails,
)
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.users import (
    LoginSessionView,
    OtpChallengeView,
    StartOtpLoginCommand,
    VerifyOtpLoginCommand,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    InvalidPhoneNumberError,
    NotFoundError,
    UnknownCountryError,
    UnsupportedLanguageError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.localization.constrained_integers import CountryCallingCode
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    EmergencyNumber,
    LanguageTag,
    ScriptCode,
    TimezoneName,
)
from app.schemas.typings.localization.strings import (
    CountryDisplayName,
    FormattedPhoneNumber,
    LanguageDisplayName,
    LocalizedTextValue,
    RawPhoneNumberInput,
)
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken, RawEmailAddressInput
from app.transformers.businesses.business_view_transformer import (
    BusinessViewTransformer,
)
from app.transformers.users.user_view_transformer import UserViewTransformer
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.businesses.create_business_use_case import CreateBusinessUseCase
from app.use_cases.businesses.get_business_use_case import GetBusinessUseCase
from app.use_cases.businesses.change_member_role_use_case import (
    ChangeMemberRoleUseCase,
)
from app.use_cases.businesses.invite_staff_use_case import InviteStaffUseCase
from app.use_cases.businesses.list_my_businesses_use_case import (
    ListMyBusinessesUseCase,
)
from app.use_cases.businesses.remove_member_use_case import RemoveMemberUseCase
from app.use_cases.businesses.update_business_settings_use_case import (
    UpdateBusinessSettingsUseCase,
)
from app.use_cases.compliance.accept_dpa_use_case import AcceptDpaUseCase
from app.use_cases.compliance.collect_contact_records_use_case import (
    CollectContactRecordsUseCase,
)
from app.use_cases.compliance.delete_contact_data_use_case import (
    DeleteContactDataUseCase,
)
from app.use_cases.compliance.export_contact_data_use_case import (
    ExportContactDataUseCase,
)
from app.use_cases.compliance.get_dpa_status_use_case import GetDpaStatusUseCase
from app.use_cases.compliance.list_audit_log_use_case import ListAuditLogUseCase
from app.use_cases.compliance.purge_expired_recordings_use_case import (
    PurgeExpiredRecordingsUseCase,
)
from app.use_cases.users.authenticate_user_use_case import AuthenticateUserUseCase
from app.use_cases.users.get_current_user_use_case import GetCurrentUserUseCase
from app.use_cases.users.logout_use_case import LogoutUseCase
from app.use_cases.users.start_otp_login_use_case import StartOtpLoginUseCase
from app.use_cases.users.update_current_user_use_case import (
    UpdateCurrentUserUseCase,
)
from app.use_cases.users.verify_otp_login_use_case import VerifyOtpLoginUseCase
from app.utilities.config_helpers.app_settings_assembler import assemble_app_settings

START_UNIX_NANOSECONDS: int = 1_790_000_000_000_000_000
NANOSECONDS_PER_SECOND: int = 1_000_000_000
SECONDS_PER_DAY: int = 24 * 60 * 60

# Example mobile numbers (valid in their numbering plans) per country.
GEORGIA_MOBILE: str = "+995 555 12 34 56"
USA_MOBILE: str = "+1 201-555-0123"
BRAZIL_MOBILE: str = "+55 11 96123-4567"
INDIA_MOBILE: str = "+91 81234 56789"
GERMANY_MOBILE: str = "+49 1512 3456789"
ISRAEL_MOBILE: str = "+972 50-234-5678"
UAE_MOBILE: str = "+971 50 123 4567"
JAPAN_MOBILE: str = "+81 90-1234-5678"
NORTH_KOREA_MOBILE: str = "+850 192 123 4567"
IRAN_MOBILE: str = "+98 912 345 6789"
MONACO_MOBILE: str = "+377 6 12 34 56 78"


class RecordingVoiceAgentRemoval:
    """Records the businesses whose voice agent was switched off."""

    def __init__(self) -> None:
        self.business_ids: list[BusinessId] = []

    def run(self, input_data: BusinessId) -> None:
        self.business_ids.append(input_data)


class RecordingAssistantResumption:
    """Resumes a paused business the way re-activation would, and records it."""

    def __init__(self) -> None:
        self.business_ids: list[BusinessId] = []

    def run(self, input_data: BusinessDocument) -> None:
        self.business_ids.append(input_data.id)
        input_data.status = BusinessStatus.LIVE


class AdjustableClock:
    """Unix time in nanoseconds that tests move forward explicitly."""

    def __init__(self, start_nanoseconds: int = START_UNIX_NANOSECONDS) -> None:
        self.nanoseconds: int = start_nanoseconds

    def read(self) -> int:
        return self.nanoseconds

    def advance(self, seconds: int) -> None:
        self.nanoseconds += seconds * NANOSECONDS_PER_SECOND

    def build_wall_clock(self) -> WallClock[Microseconds]:
        return WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=self.read,
        )

    def now_microseconds(self) -> Microseconds:
        return Microseconds(self.nanoseconds // 1000)

    def microseconds_ago(self, seconds: int) -> Microseconds:
        return Microseconds((self.nanoseconds // 1000) - seconds * 1_000_000)


PHONE_NUMBER_KINDS: dict[int, PhoneNumberKind] = {
    PhoneNumberType.MOBILE: PhoneNumberKind.MOBILE,
    PhoneNumberType.FIXED_LINE: PhoneNumberKind.FIXED_LINE,
    PhoneNumberType.FIXED_LINE_OR_MOBILE: PhoneNumberKind.FIXED_LINE_OR_MOBILE,
    PhoneNumberType.TOLL_FREE: PhoneNumberKind.TOLL_FREE,
    PhoneNumberType.VOIP: PhoneNumberKind.VOIP,
}


class PhonenumbersParser(PhoneNumberParserContract):
    """Test parser over the real numbering plans of every country."""

    def parse(
        self,
        raw_phone_number: RawPhoneNumberInput,
        country_hint: CountryCode | None,
    ) -> PhoneNumberDetails:
        try:
            number = phonenumbers.parse(
                str(raw_phone_number),
                None if country_hint is None else str(country_hint),
            )
        except NumberParseException as error:
            raise InvalidPhoneNumberError("Not a phone number.") from error

        region: str | None = phonenumbers.region_code_for_number(number)
        if not phonenumbers.is_valid_number(number) or region is None:
            raise InvalidPhoneNumberError("Not a valid phone number.")

        kind: PhoneNumberKind = PHONE_NUMBER_KINDS.get(
            phonenumbers.number_type(number),
            PhoneNumberKind.OTHER,
        )
        return PhoneNumberDetails(
            e164=E164PhoneNumber(
                phonenumbers.format_number(number, PhoneNumberFormat.E164)
            ),
            country_code=CountryCode(region),
            calling_code=CountryCallingCode(number.country_code or 0),
            kind=kind,
            is_mobile=kind
            in (PhoneNumberKind.MOBILE, PhoneNumberKind.FIXED_LINE_OR_MOBILE),
            international_format=FormattedPhoneNumber(
                phonenumbers.format_number(number, PhoneNumberFormat.INTERNATIONAL)
            ),
            national_format=FormattedPhoneNumber(
                phonenumbers.format_number(number, PhoneNumberFormat.NATIONAL)
            ),
            timezones=[
                TimezoneName(zone)
                for zone in phone_timezones.time_zones_for_number(number)
                if zone != "Etc/Unknown"
            ],
        )


def build_country(
    code: str,
    name: str,
    calling_code: int,
    currency: str,
    timezones: list[str],
    languages: list[str],
    owner_language: str,
    emergency_number: str,
    otp_channels: list[OtpDeliveryChannel],
    data_region: DataRegion = DataRegion.EU,
    status: CountryOnboardingStatus = CountryOnboardingStatus.SUPPORTED,
    recording_rule: RecordingConsentRule = RecordingConsentRule.NOTICE,
) -> CountryProfile:
    return CountryProfile(
        country_code=CountryCode(code),
        english_name=CountryDisplayName(name),
        calling_code=CountryCallingCode(calling_code),
        currency_code=CurrencyCode(currency),
        timezones=[TimezoneName(zone) for zone in timezones],
        default_timezone=TimezoneName(timezones[0]),
        default_customer_languages=[LanguageTag(tag) for tag in languages],
        default_owner_language=LanguageTag(owner_language),
        emergency_number=EmergencyNumber(emergency_number),
        data_region=data_region,
        onboarding_status=status,
        otp_delivery_channels=otp_channels,
        local_number_provisioning=LocalNumberProvisioning.AVAILABLE,
        recording_consent_rule=recording_rule,
    )


SMS: OtpDeliveryChannel = OtpDeliveryChannel.SMS
WHATSAPP: OtpDeliveryChannel = OtpDeliveryChannel.WHATSAPP
TELEGRAM: OtpDeliveryChannel = OtpDeliveryChannel.TELEGRAM
EMAIL_CHANNEL: OtpDeliveryChannel = OtpDeliveryChannel.EMAIL

COUNTRY_PROFILES: list[CountryProfile] = [
    build_country(
        "AE", "United Arab Emirates", 971, "AED", ["Asia/Dubai"],
        ["ar", "en"], "ar", "999", [WHATSAPP, SMS],
        status=CountryOnboardingStatus.PILOT,
    ),
    build_country(
        "BR", "Brazil", 55, "BRL", ["America/Sao_Paulo", "America/Manaus"],
        ["pt-BR", "en", "es"], "pt-BR", "190", [WHATSAPP, SMS],
        status=CountryOnboardingStatus.PILOT,
    ),
    build_country(
        "DE", "Germany", 49, "EUR", ["Europe/Berlin"], ["de", "en"], "de", "112",
        [SMS],
    ),
    build_country(
        "GE", "Georgia", 995, "GEL", ["Asia/Tbilisi"], ["ka", "ru", "en"], "ka",
        "112", [SMS, WHATSAPP, TELEGRAM],
    ),
    build_country(
        "IL", "Israel", 972, "ILS", ["Asia/Jerusalem"], ["he", "en", "ru", "ar"],
        "he", "100", [WHATSAPP, SMS],
    ),
    build_country(
        "IN", "India", 91, "INR", ["Asia/Kolkata"], ["hi", "en"], "en", "112",
        [SMS, WHATSAPP],
    ),
    build_country(
        "IR", "Iran", 98, "IRR", ["Asia/Tehran"], ["fa", "en"], "fa", "110", [SMS],
    ),
    build_country(
        "JP", "Japan", 81, "JPY", ["Asia/Tokyo"], ["ja", "en"], "ja", "110", [SMS],
    ),
    build_country(
        "KP", "North Korea", 850, "KPW", ["Asia/Pyongyang"], ["ko"], "ko", "119",
        [SMS], status=CountryOnboardingStatus.RESTRICTED,
    ),
    build_country(
        "MC", "Monaco", 377, "EUR", ["Europe/Monaco"], ["fr", "en"], "fr", "112",
        [EMAIL_CHANNEL],
    ),
    build_country(
        "US", "United States", 1, "USD",
        ["America/New_York", "America/Chicago", "America/Los_Angeles"],
        ["en", "es"], "en", "911", [SMS], data_region=DataRegion.US,
        status=CountryOnboardingStatus.PILOT,
        recording_rule=RecordingConsentRule.ALL_PARTY_CONSENT,
    ),
]  # fmt: skip


class FakeCountryRegistry(CountryRegistryContract):
    def __init__(self) -> None:
        self._profiles: dict[CountryCode, CountryProfile] = {
            profile.country_code: profile for profile in COUNTRY_PROFILES
        }

    def get(self, country_code: CountryCode) -> CountryProfile:
        profile: CountryProfile | None = self._profiles.get(country_code)
        if profile is None:
            raise UnknownCountryError(f"Unknown country {country_code}.")

        return profile

    def list_all(self) -> list[CountryProfile]:
        return sorted(self._profiles.values(), key=lambda profile: profile.country_code)


def build_language(
    tag: str,
    english_name: str,
    native_name: str,
    script: str,
    direction: TextDirection = TextDirection.LEFT_TO_RIGHT,
    voice_support: LanguageVoiceSupport = LanguageVoiceSupport.VERIFIED,
) -> LanguageProfile:
    return LanguageProfile(
        tag=LanguageTag(tag),
        english_name=LanguageDisplayName(english_name),
        native_name=LanguageDisplayName(native_name),
        script=ScriptCode(script),
        direction=direction,
        text_support=LanguageTextSupport.SUPPORTED,
        voice_support=voice_support,
    )


RTL: TextDirection = TextDirection.RIGHT_TO_LEFT
LANGUAGE_PROFILES: list[LanguageProfile] = [
    build_language("ar", "Arabic", "العربية", "Arab", RTL),
    build_language("de", "German", "Deutsch", "Latn"),
    build_language("en", "English", "English", "Latn"),
    build_language("es", "Spanish", "Español", "Latn"),
    build_language("fa", "Persian", "فارسی", "Arab", RTL),
    build_language("fr", "French", "Français", "Latn"),
    build_language("he", "Hebrew", "עברית", "Hebr", RTL),
    build_language("hi", "Hindi", "हिन्दी", "Deva"),
    build_language("hy", "Armenian", "Հայերեն", "Armn"),
    build_language("ja", "Japanese", "日本語", "Jpan"),
    build_language(
        "ka", "Georgian", "ქართული", "Geor",
        voice_support=LanguageVoiceSupport.NEEDS_PILOT_CHECK,
    ),
    build_language("ko", "Korean", "한국어", "Kore"),
    build_language("pt", "Portuguese", "Português", "Latn"),
    build_language("pt-BR", "Brazilian Portuguese", "Português (Brasil)", "Latn"),
    build_language("ru", "Russian", "Русский", "Cyrl"),
    build_language("tr", "Turkish", "Türkçe", "Latn"),
]  # fmt: skip


class FakeLanguageRegistry(LanguageRegistryContract):
    def __init__(self) -> None:
        self._profiles: dict[LanguageTag, LanguageProfile] = {
            profile.tag: profile for profile in LANGUAGE_PROFILES
        }

    def get(self, language_tag: LanguageTag) -> LanguageProfile:
        profile: LanguageProfile | None = self._profiles.get(language_tag)
        if profile is None:
            raise UnsupportedLanguageError(f"Unsupported language {language_tag}.")

        return profile

    def list_all(self) -> list[LanguageProfile]:
        return list(self._profiles.values())


def build_niche(key: NicheKey, recommended_plans: list[PlanKey]) -> NicheTemplate:
    text = LocalizedText(values={LanguageTag("en"): LocalizedTextValue(key.value)})
    return NicheTemplate(
        key=key,
        wave=LaunchWave.A,
        names=text,
        descriptions=text,
        recommended_plans=recommended_plans,
        resource_kind=ResourceKind.TABLE,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text,
        knowledge_kinds=[KnowledgeItemKind.FAQ],
        questions=[],
        prompt_rules=[],
        default_handoff_rules=text,
        default_forbidden_rules=text,
        autotest_kinds=[AutotestScenarioKind.BOOKING],
    )


class FakeNicheTemplateRegistry(NicheTemplateRegistryContract):
    def __init__(self) -> None:
        self._templates: dict[NicheKey, NicheTemplate] = {
            NicheKey.RESTAURANT: build_niche(
                NicheKey.RESTAURANT,
                [PlanKey.VOICE_AND_CHAT, PlanKey.CHAT],
            ),
            NicheKey.HOTEL: build_niche(NicheKey.HOTEL, [PlanKey.PLUS]),
            NicheKey.ENTERTAINMENT: build_niche(
                NicheKey.ENTERTAINMENT,
                [PlanKey.CHAT, PlanKey.VOICE_AND_CHAT],
            ),
            NicheKey.CLINIC: build_niche(NicheKey.CLINIC, []),
        }

    def get(self, niche_key: NicheKey) -> NicheTemplate:
        template: NicheTemplate | None = self._templates.get(niche_key)
        if template is None:
            raise NotFoundError(f"Niche {niche_key} has no template.")

        return template

    def list_all(self) -> list[NicheTemplate]:
        return list(self._templates.values())


@dataclass(frozen=True)
class DeliveredOtp:
    delivery_channel: OtpDeliveryChannel
    phone_number: E164PhoneNumber | None
    email: EmailAddress | None
    code: OtpCode
    language_tag: LanguageTag


class RecordingOtpDelivery(OtpDeliveryFacilitatorContract):
    """
    Keeps every delivered code so tests can type it back. Tests narrow the
    configured channels and make single channels (or all) fail.
    """

    def __init__(self) -> None:
        self.deliveries: list[DeliveredOtp] = []
        self.attempted_channels: list[OtpDeliveryChannel] = []
        self.is_failing: bool = False
        self.failing_channels: set[OtpDeliveryChannel] = set()
        self.channels: frozenset[OtpDeliveryChannel] = frozenset(OtpDeliveryChannel)

    def available_channels(self) -> frozenset[OtpDeliveryChannel]:
        return self.channels

    def deliver(
        self,
        delivery_channel: OtpDeliveryChannel,
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        code: OtpCode,
        language_tag: LanguageTag,
    ) -> None:
        self.attempted_channels.append(delivery_channel)
        if self.is_failing or delivery_channel in self.failing_channels:
            raise ExternalServiceError(f"{delivery_channel.value} provider is down.")

        self.deliveries.append(
            DeliveredOtp(
                delivery_channel=delivery_channel,
                phone_number=phone_number,
                email=email,
                code=code,
                language_tag=language_tag,
            )
        )

    def last_code(self) -> OtpCode:
        return self.deliveries[-1].code


class InMemoryRecordingStorage(RecordingStorageAdapterContract):
    def __init__(self) -> None:
        self.deleted_paths: list[RecordingStoragePath] = []
        self.is_failing: bool = False

    def delete(self, recording_path: RecordingStoragePath) -> None:
        if self.is_failing:
            raise ExternalServiceError("Recording storage is unavailable.")

        self.deleted_paths.append(recording_path)


class AccountsTestbed:
    """Every repository, fake and use case of the accounts slice, wired."""

    def __init__(self, environment_variables: Mapping[str, str]) -> None:
        self.clock: AdjustableClock = AdjustableClock()
        wall_clock: WallClock[Microseconds] = self.clock.build_wall_clock()
        self.settings: AppSettings = assemble_app_settings(environment_variables)
        self.country_registry: FakeCountryRegistry = FakeCountryRegistry()
        self.language_registry: FakeLanguageRegistry = FakeLanguageRegistry()
        self.niche_registry: FakeNicheTemplateRegistry = FakeNicheTemplateRegistry()
        self.phone_parser: PhonenumbersParser = PhonenumbersParser()
        self.otp_delivery: RecordingOtpDelivery = RecordingOtpDelivery()
        self.recording_storage: InMemoryRecordingStorage = InMemoryRecordingStorage()

        self.user_collection = InMemoryDocumentCollectionAdapter[UserDocument](
            UserDocument
        )
        self.user_repo = UserRepository(self.user_collection)
        self.otp_challenge_repo = OtpChallengeRepository(
            InMemoryDocumentCollectionAdapter[OtpChallengeDocument](
                OtpChallengeDocument
            )
        )
        self.user_session_repo = UserSessionRepository(
            InMemoryDocumentCollectionAdapter[UserSessionDocument](UserSessionDocument)
        )
        self.business_repo = BusinessRepository(
            InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
        )
        self.audit_log_collection = InMemoryDocumentCollectionAdapter[
            AuditLogEntryDocument
        ](AuditLogEntryDocument)
        self.audit_log_repo = AuditLogRepository(self.audit_log_collection)
        self.dpa_acceptance_repo = DpaAcceptanceRepository(
            InMemoryDocumentCollectionAdapter[DpaAcceptanceDocument](
                DpaAcceptanceDocument
            )
        )
        self.contact_repo = ContactRepository(
            InMemoryDocumentCollectionAdapter[ContactDocument](ContactDocument)
        )
        self.conversation_repo = ConversationRepository(
            InMemoryDocumentCollectionAdapter[ConversationDocument](
                ConversationDocument
            )
        )
        self.message_repo = MessageRepository(
            InMemoryDocumentCollectionAdapter[MessageDocument](MessageDocument)
        )
        self.llm_turn_repo = LlmTurnRepository(
            InMemoryDocumentCollectionAdapter[LlmTurnDocument](LlmTurnDocument)
        )
        self.call_repo = CallRepository(
            InMemoryDocumentCollectionAdapter[CallDocument](CallDocument)
        )
        self.booking_repo = BookingRepository(
            InMemoryDocumentCollectionAdapter[BookingDocument](BookingDocument)
        )
        self.lead_repo = LeadRepository(
            InMemoryDocumentCollectionAdapter[LeadDocument](LeadDocument)
        )
        self.handoff_repo = HandoffRepository(
            InMemoryDocumentCollectionAdapter[HandoffDocument](HandoffDocument)
        )
        self.subscription_repo = SubscriptionRepository(
            InMemoryDocumentCollectionAdapter[SubscriptionDocument](
                SubscriptionDocument
            )
        )

        user_view_transformer = UserViewTransformer()
        business_view_transformer = BusinessViewTransformer()
        self.authorize_business_access = AuthorizeBusinessAccessUseCase(
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )

        self.start_otp_login = StartOtpLoginUseCase(
            otp_challenge_repo=self.otp_challenge_repo,
            phone_number_parser=self.phone_parser,
            country_registry=self.country_registry,
            language_registry=self.language_registry,
            otp_delivery_facilitator=self.otp_delivery,
            app_settings=self.settings,
            wall_clock=wall_clock,
        )
        self.verify_otp_login = VerifyOtpLoginUseCase(
            otp_challenge_repo=self.otp_challenge_repo,
            user_repo=self.user_repo,
            user_session_repo=self.user_session_repo,
            audit_log_repo=self.audit_log_repo,
            user_view_transformer=user_view_transformer,
            app_settings=self.settings,
            wall_clock=wall_clock,
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

        collect_contact_records = CollectContactRecordsUseCase(
            contact_repo=self.contact_repo,
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
            call_repo=self.call_repo,
            booking_repo=self.booking_repo,
            lead_repo=self.lead_repo,
            handoff_repo=self.handoff_repo,
        )
        self.accept_dpa = AcceptDpaUseCase(
            authorize_business_access=self.authorize_business_access,
            dpa_acceptance_repo=self.dpa_acceptance_repo,
            audit_log_repo=self.audit_log_repo,
            app_settings=self.settings,
            wall_clock=wall_clock,
        )
        self.get_dpa_status = GetDpaStatusUseCase(
            authorize_business_access=self.authorize_business_access,
            dpa_acceptance_repo=self.dpa_acceptance_repo,
            app_settings=self.settings,
        )
        self.list_audit_log = ListAuditLogUseCase(
            authorize_business_access=self.authorize_business_access,
            audit_log_repo=self.audit_log_repo,
        )
        self.export_contact_data = ExportContactDataUseCase(
            authorize_business_access=self.authorize_business_access,
            collect_contact_records=collect_contact_records,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )
        self.delete_contact_data = DeleteContactDataUseCase(
            authorize_business_access=self.authorize_business_access,
            collect_contact_records=collect_contact_records,
            contact_repo=self.contact_repo,
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
            llm_turn_repo=self.llm_turn_repo,
            call_repo=self.call_repo,
            booking_repo=self.booking_repo,
            lead_repo=self.lead_repo,
            handoff_repo=self.handoff_repo,
            recording_storage=self.recording_storage,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )
        self.purge_expired_recordings = PurgeExpiredRecordingsUseCase(
            business_repo=self.business_repo,
            call_repo=self.call_repo,
            recording_storage=self.recording_storage,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )

    def request_phone_code(
        self,
        raw_phone_number: str,
        country_hint: str | None = None,
    ) -> OtpChallengeView:
        hint: CountryCode | None = (
            None if country_hint is None else CountryCode(country_hint)
        )
        return self.start_otp_login.run(
            StartOtpLoginCommand(
                phone_number=RawPhoneNumberInput(raw_phone_number),
                country_hint=hint,
            )
        )

    def sign_in_with_phone(
        self,
        raw_phone_number: str,
        country_hint: str | None = None,
    ) -> LoginSessionView:
        challenge: OtpChallengeView = self.request_phone_code(
            raw_phone_number,
            country_hint,
        )
        return self.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id,
                code=self.otp_delivery.last_code(),
            )
        )

    def sign_in_with_email(self, raw_email: str) -> LoginSessionView:
        challenge: OtpChallengeView = self.start_otp_login.run(
            StartOtpLoginCommand(email=RawEmailAddressInput(raw_email))
        )
        return self.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id,
                code=self.otp_delivery.last_code(),
            )
        )

    def create_restaurant(
        self,
        owner_id: UserId,
        name: str = "Trattoria",
    ) -> BusinessDocument:
        view = self.create_business.run(
            CreateBusinessCommand(
                user_id=owner_id,
                details=CreateBusinessRequest(
                    name=BusinessName(name),
                    niche_key=NicheKey.RESTAURANT,
                ),
            )
        )
        business: BusinessDocument | None = self.business_repo.get(view.id)
        assert business is not None
        return business

    def build_http_client(self) -> TestClient:
        """FastAPI app with the three accounts routers over this testbed."""

        current_user = build_current_user_dependency(
            PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(self.authenticate_user))
            )
        )
        http_application = FastAPI()
        install_error_handlers(http_application)
        http_application.include_router(
            build_users_router(
                start_otp_login_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.start_otp_login))
                ),
                verify_otp_login_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.verify_otp_login))
                ),
                logout_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.logout))
                ),
                get_current_user_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.get_current_user))
                ),
                update_current_user_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.update_current_user))
                ),
                current_user=current_user,
            )
        )
        http_application.include_router(
            build_business_router(
                create_business_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.create_business))
                ),
                list_my_businesses_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.list_my_businesses))
                ),
                get_business_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.get_business))
                ),
                update_business_settings_operator=PipelineOperator(
                    OrchestratorPipeline(
                        UseCaseOrchestrator(self.update_business_settings)
                    )
                ),
                invite_staff_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.invite_staff))
                ),
                remove_member_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.remove_member))
                ),
                change_member_role_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.change_member_role))
                ),
                current_user=current_user,
            )
        )
        http_application.include_router(
            build_compliance_router(
                get_dpa_status_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.get_dpa_status))
                ),
                accept_dpa_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.accept_dpa))
                ),
                list_audit_log_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.list_audit_log))
                ),
                export_contact_data_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.export_contact_data))
                ),
                delete_contact_data_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.delete_contact_data))
                ),
                current_user=current_user,
            )
        )
        return TestClient(http_application)


def build_accounts_testbed(
    environment_variables: Mapping[str, str] | None = None,
) -> AccountsTestbed:
    return AccountsTestbed(environment_variables or {})


def bearer(access_token: AccessToken) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
