from typed_time_provider import Microseconds

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.knowledge.constrained_strings import KnowledgeTag
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId
from tests.foundation.builders import build_business


def test_business_document_survives_json_round_trip() -> None:
    business = build_business(UserId())

    restored = BusinessDocument.model_validate_json(business.model_dump_json())

    assert restored == business
    assert type(restored.id) is type(business.id)
    assert type(restored.languages[0]) is LanguageTag
    assert isinstance(restored.created_at, Microseconds)


def test_user_from_any_country_is_stored_in_e164() -> None:
    user = UserDocument(
        login_method=LoginMethod.PHONE,
        phone_number=E164PhoneNumber("+5511912345678"),
        country_code=CountryCode("BR"),
        locale=LanguageTag("pt-BR"),
    )

    restored = UserDocument.model_validate_json(user.model_dump_json())

    assert restored.phone_number == "+5511912345678"
    assert restored.locale == "pt-BR"


def test_knowledge_prices_are_integers_in_the_business_currency() -> None:
    business = build_business(UserId())
    item = KnowledgeItemDocument(
        business_id=business.id,
        kind=KnowledgeItemKind.MENU_ITEM,
        title=KnowledgeTitle("Khachapuri Adjaruli"),
        price_minor=MoneyAmountMinor(1800),
        currency_code=CurrencyCode("GEL"),
        tags=[KnowledgeTag("vegetarian")],
    )

    restored = KnowledgeItemDocument.model_validate_json(item.model_dump_json())

    assert restored.price_minor == 1800
    assert type(restored.price_minor) is MoneyAmountMinor
    assert restored.tags == ["vegetarian"]
