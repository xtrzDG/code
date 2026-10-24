"""
Reading Twilio's phone-number answers: available numbers, the price list
and the error codes the purchase flow tells apart.
"""

from decimal import Decimal, InvalidOperation

from app.schemas.constants.phone_numbers import PhoneNumberType
from app.schemas.dto.phone_numbers.provisioning import AvailablePhoneNumber
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.telephony.strings import PhoneNumberLocality, PhoneNumberRegion
from app.utilities.channels.json_values import (
    JsonObject,
    read_object,
    read_objects,
    read_text,
)

# The path segment of each kind in the AvailablePhoneNumbers resource.
AVAILABLE_NUMBERS_RESOURCE: dict[PhoneNumberType, str] = {
    PhoneNumberType.LOCAL: "Local",
    PhoneNumberType.MOBILE: "Mobile",
    PhoneNumberType.TOLL_FREE: "TollFree",
}
# The `number_type` of each kind in the Pricing API's price list.
PRICE_LIST_NUMBER_TYPE: dict[PhoneNumberType, str] = {
    PhoneNumberType.LOCAL: "local",
    PhoneNumberType.MOBILE: "mobile",
    PhoneNumberType.TOLL_FREE: "toll free",
}
PRICE_UNIT: str = "USD"
MICRO_UNITS_PER_DOLLAR: Decimal = Decimal(1_000_000)
# 21422 "PhoneNumber Requested is not available": taken since the search,
# reserved or no longer sold.
UNAVAILABLE_NUMBER_CODES: frozenset[int] = frozenset({21422})


def read_available_numbers(body: JsonObject) -> list[AvailablePhoneNumber]:
    """
    The numbers of an AvailablePhoneNumbers page that take calls and need no
    address; a malformed entry is skipped, never guessed at.
    """

    numbers: list[AvailablePhoneNumber] = []
    for entry in read_objects(body, "available_phone_numbers"):
        phone_number: str | None = read_text(entry, "phone_number")
        capabilities: JsonObject = read_object(entry, "capabilities") or {}
        if (
            phone_number is None
            or capabilities.get("voice") is not True
            or read_text(entry, "address_requirements") not in (None, "none")
        ):
            continue

        try:
            e164 = E164PhoneNumber(phone_number)
        except ValueError:
            continue

        locality: str | None = read_text(entry, "locality")
        region: str | None = read_text(entry, "region")
        numbers.append(
            AvailablePhoneNumber(
                phone_number=e164,
                locality=None if locality is None else PhoneNumberLocality(locality),
                region=None if region is None else PhoneNumberRegion(region),
            )
        )

    return numbers


def read_monthly_price(
    body: JsonObject, number_type: PhoneNumberType
) -> CostMicroUsd | None:
    """
    The current monthly price of the kind in a country's price list, in
    millionths of a dollar; None when the list prices it in another
    currency, has no such kind, or is malformed.
    """

    if read_text(body, "price_unit") != PRICE_UNIT:
        return None

    wanted: str = PRICE_LIST_NUMBER_TYPE[number_type]
    for price in read_objects(body, "phone_number_prices"):
        if read_text(price, "number_type") != wanted:
            continue

        amount: str | None = read_text(price, "current_price") or read_text(
            price, "base_price"
        )
        if amount is None:
            return None

        try:
            micro_dollars: Decimal = Decimal(amount) * MICRO_UNITS_PER_DOLLAR
        except InvalidOperation:
            return None

        if not micro_dollars.is_finite() or micro_dollars <= 0:
            return None

        return CostMicroUsd(int(micro_dollars.to_integral_value()))

    return None
