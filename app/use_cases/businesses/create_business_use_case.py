from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import (
    CountryRegistryContract,
    LanguageRegistryContract,
    NicheTemplateRegistryContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.localization import CountryOnboardingStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.users import UserDocument
from app.schemas.dto.businesses import (
    BusinessView,
    BusinessViewSource,
    CreateBusinessCommand,
    CreateBusinessRequest,
)
from app.schemas.dto.localization import CountryProfile
from app.schemas.dto.niches import NicheTemplate
from app.schemas.exceptions.application_errors import (
    CountryRestrictedError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.strings import CityName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
    TimezoneName,
)
from app.utilities.businesses.business_settings_validation import (
    MAX_BUSINESS_LANGUAGES,
    require_existing_timezone,
    require_valid_business_name,
    require_valid_city_name,
    validate_business_languages,
)


class CreateBusinessUseCase(UseCaseContract[CreateBusinessCommand, BusinessView]):
    """
    Create a business (tenant) whose creator becomes its owner.

    The country (by default the creator's phone country) supplies every
    regional default: time zone, customer languages, currency and data
    region; nothing is assumed about one country. Explicit choices are
    validated: the time zone against the IANA database, languages against
    the language registry (1 to 10, without repeats), the default language
    against the chosen languages. The plan defaults to the niche's first
    recommended plan and recording retention to the platform default.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        user_repo: UserRepoContract,
        country_registry: CountryRegistryContract,
        language_registry: LanguageRegistryContract,
        niche_template_registry: NicheTemplateRegistryContract,
        business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ],
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._user_repo: UserRepoContract = user_repo
        self._country_registry: CountryRegistryContract = country_registry
        self._language_registry: LanguageRegistryContract = language_registry
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._business_view_transformer: TransformerContract[
            BusinessViewSource,
            BusinessView,
        ] = business_view_transformer
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CreateBusinessCommand) -> BusinessView:
        details: CreateBusinessRequest = input_data.details
        owner: UserDocument | None = self._user_repo.get(input_data.user_id)
        if owner is None:
            raise NotFoundError(f"User {input_data.user_id} was not found.")

        require_valid_business_name(details.name)
        city: CityName | None = details.city
        if city is not None:
            require_valid_city_name(city)
            if city.strip() == "":
                city = None

        country: CountryProfile = self._load_allowed_country(
            details.country_code or owner.country_code
        )
        timezone: TimezoneName = details.timezone or country.default_timezone
        require_existing_timezone(timezone)
        languages: list[LanguageTag] = self._choose_languages(details, country)
        owner_language: LanguageTag = details.owner_language or owner.locale
        self._language_registry.get(owner_language)
        plan_key: PlanKey = details.plan_key or self._recommended_plan(details)

        now: Microseconds = self._wall_clock.now_unix()
        business = BusinessDocument(
            name=details.name,
            niche_key=details.niche_key,
            country_code=country.country_code,
            city=city,
            timezone=timezone,
            currency_code=country.currency_code,
            languages=languages,
            default_language=self._choose_default_language(details, languages),
            owner_language=owner_language,
            plan_key=plan_key,
            data_region=country.data_region,
            members=[BusinessMember(user_id=owner.id, role=BusinessMemberRole.OWNER)],
            recording_retention_days=(
                self._app_settings.default_recording_retention_days
            ),
            created_at=now,
            updated_at=now,
        )
        self._business_repo.save(business)
        return self._business_view_transformer.transform(
            BusinessViewSource(
                business=business,
                member_users=[owner],
                viewer_id=owner.id,
            )
        )

    def _load_allowed_country(self, country_code: CountryCode | None) -> CountryProfile:
        if country_code is None:
            raise ValidationFailedError(
                "Choose the country of the business; it sets the time zone, "
                "languages and currency."
            )

        country: CountryProfile = self._country_registry.get(country_code)
        if (
            country.onboarding_status is CountryOnboardingStatus.RESTRICTED
            or country_code in self._app_settings.restricted_country_codes
        ):
            raise CountryRestrictedError(
                f"Businesses from country {str(country_code)} cannot be onboarded."
            )

        return country

    def _choose_languages(
        self,
        details: CreateBusinessRequest,
        country: CountryProfile,
    ) -> list[LanguageTag]:
        if details.languages is not None:
            return validate_business_languages(
                details.languages,
                self._language_registry,
            )

        country_languages: list[LanguageTag] = list(
            dict.fromkeys(country.default_customer_languages)
        )[:MAX_BUSINESS_LANGUAGES]
        if not country_languages:
            return [country.default_owner_language]

        return country_languages

    def _choose_default_language(
        self,
        details: CreateBusinessRequest,
        languages: list[LanguageTag],
    ) -> LanguageTag:
        if details.default_language is None:
            return languages[0]

        if details.default_language not in languages:
            raise ValidationFailedError(
                "The default language must be one of the business languages."
            )

        return details.default_language

    def _recommended_plan(self, details: CreateBusinessRequest) -> PlanKey:
        niche: NicheTemplate = self._niche_template_registry.get(details.niche_key)
        if not niche.recommended_plans:
            raise ValidationFailedError("Choose a plan for this niche.")

        return niche.recommended_plans[0]
