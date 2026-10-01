from typed_time_provider import Microseconds

from app.schemas.constants.accounts import LoginMethod
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.owners import OwnerDocument
from app.schemas.typings.accounts.prefixed_id import OwnerId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)


def test_business_document_survives_json_round_trip() -> None:
    business = BusinessDocument(
        owner_id=OwnerId(),
        name=BusinessName("VR Club Tbilisi"),
        niche_key=NicheKey.ENTERTAINMENT,
        country_code=CountryCode("GE"),
        timezone=TimezoneName("Asia/Tbilisi"),
        currency_code=CurrencyCode("GEL"),
        owner_language=LanguageTag("ru"),
        customer_languages=[LanguageTag("ka"), LanguageTag("ru"), LanguageTag("en")],
        plan_key=PlanKey.VOICE_AND_CHAT,
        data_region=DataRegion.EU,
    )

    restored = BusinessDocument.model_validate_json(business.model_dump_json())

    assert restored == business
    assert type(restored.id) is type(business.id)
    assert type(restored.customer_languages[0]) is LanguageTag
    assert isinstance(restored.created_at, Microseconds)


def test_owner_from_any_country_is_stored_in_e164() -> None:
    owner = OwnerDocument(
        login_method=LoginMethod.PHONE,
        phone_number=E164PhoneNumber("+5511912345678"),
        country_code=CountryCode("BR"),
        preferred_language=LanguageTag("pt-BR"),
    )

    restored = OwnerDocument.model_validate_json(owner.model_dump_json())

    assert restored.phone_number == "+5511912345678"
    assert restored.preferred_language == "pt-BR"
