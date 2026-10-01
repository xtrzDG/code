import pytest

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.dto.businesses import CreateBusinessCommand, CreateBusinessRequest
from app.schemas.dto.users import UpdateCurrentUserCommand
from app.schemas.exceptions.application_errors import (
    CountryRestrictedError,
    NotFoundError,
    UnknownCountryError,
    UnsupportedLanguageError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.users.prefixed_id import UserId
from tests.users.accounts_testbed import (
    BRAZIL_MOBILE,
    GEORGIA_MOBILE,
    GERMANY_MOBILE,
    INDIA_MOBILE,
    ISRAEL_MOBILE,
    JAPAN_MOBILE,
    UAE_MOBILE,
    USA_MOBILE,
    AccountsTestbed,
    build_accounts_testbed,
)

ELEVEN_LANGUAGES: list[LanguageTag] = [
    LanguageTag(tag)
    for tag in ("ar", "de", "en", "es", "fa", "fr", "he", "hi", "hy", "ja", "ka")
]


def create(
    testbed: AccountsTestbed,
    owner_id: UserId,
    **details: object,
) -> CreateBusinessCommand:
    request = CreateBusinessRequest.model_validate(
        {"name": BusinessName("Test venue"), "niche_key": NicheKey.RESTAURANT} | details
    )
    return CreateBusinessCommand(user_id=owner_id, details=request)


@pytest.mark.parametrize(
    (
        "raw_phone_number",
        "expected_country",
        "expected_timezone",
        "expected_currency",
        "expected_languages",
        "expected_owner_language",
        "expected_region",
    ),
    [
        (
            GEORGIA_MOBILE,
            "GE",
            "Asia/Tbilisi",
            "GEL",
            ["ka", "ru", "en"],
            "ka",
            DataRegion.EU,
        ),
        (
            USA_MOBILE,
            "US",
            "America/New_York",
            "USD",
            ["en", "es"],
            "en",
            DataRegion.US,
        ),
        (
            BRAZIL_MOBILE,
            "BR",
            "America/Sao_Paulo",
            "BRL",
            ["pt-BR", "en", "es"],
            "pt-BR",
            DataRegion.EU,
        ),
        (INDIA_MOBILE, "IN", "Asia/Kolkata", "INR", ["hi", "en"], "en", DataRegion.EU),
        (
            GERMANY_MOBILE,
            "DE",
            "Europe/Berlin",
            "EUR",
            ["de", "en"],
            "de",
            DataRegion.EU,
        ),
        (
            ISRAEL_MOBILE,
            "IL",
            "Asia/Jerusalem",
            "ILS",
            ["he", "en", "ru", "ar"],
            "he",
            DataRegion.EU,
        ),
        (UAE_MOBILE, "AE", "Asia/Dubai", "AED", ["ar", "en"], "ar", DataRegion.EU),
        (JAPAN_MOBILE, "JP", "Asia/Tokyo", "JPY", ["ja", "en"], "ja", DataRegion.EU),
    ],
)
def test_country_of_the_owner_fills_every_regional_default(
    raw_phone_number: str,
    expected_country: str,
    expected_timezone: str,
    expected_currency: str,
    expected_languages: list[str],
    expected_owner_language: str,
    expected_region: DataRegion,
) -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(raw_phone_number)

    business = testbed.create_business.run(create(testbed, owner.user.id))

    assert business.country_code == expected_country
    assert business.timezone == expected_timezone
    assert business.currency_code == expected_currency
    assert business.languages == expected_languages
    assert business.default_language == expected_languages[0]
    assert business.owner_language == expected_owner_language
    assert business.data_region is expected_region
    assert business.plan_key is PlanKey.VOICE_AND_CHAT
    assert business.status is BusinessStatus.ONBOARDING
    assert business.service_mode is ServiceMode.FULL
    assert business.recording_retention_days == 90
    assert business.viewer_role is BusinessMemberRole.OWNER
    assert [(member.user_id, member.role) for member in business.members] == [
        (owner.user.id, BusinessMemberRole.OWNER)
    ]
    assert business.members[0].phone_number == owner.user.phone_number
    assert business.created_at == testbed.clock.now_microseconds()
    stored = testbed.business_repo.get(business.id)
    assert stored is not None
    assert stored.currency_code == expected_currency


def test_explicit_choices_override_country_defaults() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    business = testbed.create_business.run(
        create(
            testbed,
            owner.user.id,
            name=BusinessName("Berliner Spielhalle"),
            niche_key=NicheKey.ENTERTAINMENT,
            country_code=CountryCode("DE"),
            city=CityName("Berlin"),
            timezone=TimezoneName("Europe/Berlin"),
            languages=[
                LanguageTag("en"),
                LanguageTag("de"),
                LanguageTag("en"),
                LanguageTag("tr"),
            ],
            default_language=LanguageTag("de"),
            owner_language=LanguageTag("ru"),
            plan_key=PlanKey.PLUS,
        )
    )

    assert business.country_code == "DE"
    assert business.currency_code == "EUR"
    assert business.city == "Berlin"
    assert business.languages == ["en", "de", "tr"]
    assert business.default_language == "de"
    assert business.owner_language == "ru"
    assert business.plan_key is PlanKey.PLUS
    assert business.niche_key is NicheKey.ENTERTAINMENT


def test_owner_language_defaults_to_the_creator_interface_language() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    testbed.update_current_user.run(
        UpdateCurrentUserCommand(user_id=owner.user.id, locale=LanguageTag("ar"))
    )

    business = testbed.create_business.run(create(testbed, owner.user.id))

    assert business.owner_language == "ar"
    assert business.languages == ["he", "en", "ru", "ar"]


def test_plan_defaults_to_the_niche_recommendation_and_retention_to_settings() -> None:
    testbed = build_accounts_testbed({"RECORDING_RETENTION_DAYS": "30"})
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    hotel = testbed.create_business.run(
        create(testbed, owner.user.id, niche_key=NicheKey.HOTEL)
    )
    vr_club = testbed.create_business.run(
        create(testbed, owner.user.id, niche_key=NicheKey.ENTERTAINMENT)
    )

    assert hotel.plan_key is PlanKey.PLUS
    assert vr_club.plan_key is PlanKey.CHAT
    assert hotel.recording_retention_days == 30


def test_email_user_must_choose_a_country() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_email("owner@example.com")

    with pytest.raises(ValidationFailedError, match="country"):
        testbed.create_business.run(create(testbed, owner.user.id))

    business = testbed.create_business.run(
        create(testbed, owner.user.id, country_code=CountryCode("BR"))
    )
    assert business.currency_code == "BRL"
    assert business.owner_language == "en"


@pytest.mark.parametrize(
    ("details", "expected_error"),
    [
        ({"name": BusinessName("   ")}, ValidationFailedError),
        ({"name": BusinessName("x" * 201)}, ValidationFailedError),
        ({"city": CityName("x" * 121)}, ValidationFailedError),
        ({"timezone": TimezoneName("Mars/Olympus_Mons")}, ValidationFailedError),
        ({"timezone": TimezoneName("localtime")}, ValidationFailedError),
        ({"languages": []}, ValidationFailedError),
        ({"languages": ELEVEN_LANGUAGES}, ValidationFailedError),
        (
            {"languages": [LanguageTag("ka"), LanguageTag("xh")]},
            UnsupportedLanguageError,
        ),
        ({"default_language": LanguageTag("de")}, ValidationFailedError),
        ({"owner_language": LanguageTag("xh")}, UnsupportedLanguageError),
        ({"country_code": CountryCode("KP")}, CountryRestrictedError),
        ({"country_code": CountryCode("IR")}, CountryRestrictedError),
        ({"country_code": CountryCode("ZZ")}, UnknownCountryError),
        ({"niche_key": NicheKey.CLINIC}, ValidationFailedError),
        ({"niche_key": NicheKey.B2B_SUPPLY}, NotFoundError),
    ],
)
def test_invalid_creation_requests_are_rejected(
    details: dict[str, object],
    expected_error: type[Exception],
) -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    with pytest.raises(expected_error):
        testbed.create_business.run(create(testbed, owner.user.id, **details))

    assert testbed.business_repo.list_all() == []


def test_niche_without_recommendation_accepts_an_explicit_plan() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GERMANY_MOBILE)

    clinic = testbed.create_business.run(
        create(
            testbed,
            owner.user.id,
            niche_key=NicheKey.CLINIC,
            plan_key=PlanKey.VOICE_AND_CHAT,
        )
    )

    assert clinic.plan_key is PlanKey.VOICE_AND_CHAT


def test_blank_city_is_stored_as_missing() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    business = testbed.create_business.run(
        create(testbed, owner.user.id, city=CityName("  "))
    )

    assert business.city is None


def test_unknown_creator_is_not_found() -> None:
    testbed = build_accounts_testbed()

    with pytest.raises(NotFoundError):
        testbed.create_business.run(create(testbed, UserId()))
