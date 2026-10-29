"""The businesses a brain test world can serve, and their menu items."""

from dataclasses import dataclass

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.dto.knowledge import KnowledgeItemView
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.localization.strings import FormattedMoneyText


@dataclass(frozen=True)
class BusinessSetup:
    """A business of some country, as a test needs it."""

    name: str = "Sakhli"
    country_code: str = "GE"
    timezone: str = "Asia/Tbilisi"
    currency_code: str = "GEL"
    languages: tuple[str, ...] = ("ka", "ru", "en")
    status: BusinessStatus = BusinessStatus.LIVE


GEORGIA = BusinessSetup()
ISRAEL = BusinessSetup(
    name="Beit Kafe",
    country_code="IL",
    timezone="Asia/Jerusalem",
    currency_code="ILS",
    languages=("he", "ar", "en", "ru"),
)
ARMENIA = BusinessSetup(
    name="Ararat Grill",
    country_code="AM",
    timezone="Asia/Yerevan",
    currency_code="AMD",
    languages=("hy", "ru", "en"),
)
BRAZIL = BusinessSetup(
    name="Cantina Sol",
    country_code="BR",
    timezone="America/Sao_Paulo",
    currency_code="BRL",
    languages=("pt-BR", "en", "es"),
)


def knowledge_item(
    title: str,
    price_minor: int | None,
    currency_code: str,
    formatted_price: str | None = None,
) -> KnowledgeItemView:
    return KnowledgeItemView(
        id=KnowledgeItemId(),
        kind=KnowledgeItemKind.MENU_ITEM,
        title=KnowledgeTitle(title),
        price_minor=None if price_minor is None else MoneyAmountMinor(price_minor),
        currency_code=None if price_minor is None else CurrencyCode(currency_code),
        formatted_price=(
            None if formatted_price is None else FormattedMoneyText(formatted_price)
        ),
    )


def default_menu(setup: BusinessSetup) -> list[KnowledgeItemView]:
    return [
        knowledge_item("Adjarian khachapuri", 1800, setup.currency_code, "18,00 ₾"),
        knowledge_item("Khinkali", 120, setup.currency_code),
        knowledge_item("Chef's surprise", None, setup.currency_code),
    ]
