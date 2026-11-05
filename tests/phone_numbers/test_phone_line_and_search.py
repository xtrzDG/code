"""The phone card: what the business rents, and the owner's number search."""

import pytest

from app.schemas.constants.phone_numbers import (
    PhoneNumberAvailability,
    PhoneNumberType,
)
from app.schemas.dto.phone_numbers.phone_line import (
    PhoneLineQuery,
    PhoneNumberOfferList,
    PhoneNumberOfferQuery,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    RateLimitedError,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.telephony.constrained_strings import PhoneNumberCityQuery
from app.schemas.typings.users.prefixed_id import UserId
from tests.phone_numbers.phone_world import PhoneWorld


def search(
    world: PhoneWorld,
    user_id: UserId,
    country: str = "US",
    number_type: PhoneNumberType = PhoneNumberType.LOCAL,
    city: str | None = None,
) -> PhoneNumberOfferList:
    business = world.business_repo.list_by_member(user_id)[0]
    return world.search.run(
        PhoneNumberOfferQuery(
            user_id=user_id,
            business_id=business.id,
            country_code=CountryCode(country),
            number_type=number_type,
            city=None if city is None else PhoneNumberCityQuery(city),
            display_language=LanguageTag("en"),
        )
    )


def test_a_business_without_a_number_sees_where_it_can_have_one_at_once() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()

    line = world.get_line.run(PhoneLineQuery(user_id=owner.id, business_id=business.id))

    assert line.rented_number is None
    assert line.open_request is None
    assert line.are_numbers_self_serve is True
    assert [str(code) for code in line.self_serve_countries] == ["CA", "US"]
    # The business is in Georgia: its own country is where it looks first.
    assert str(line.default_country_code) == "GE"


def test_without_the_carrier_nothing_is_self_serve() -> None:
    world = PhoneWorld()
    world.provisioner.missing_settings = [
        EnvironmentVariableName("PHONE_NUMBER_PROVIDER")
    ]
    owner, business = world.owner_and_business()

    line = world.get_line.run(PhoneLineQuery(user_id=owner.id, business_id=business.id))
    offers = search(world, owner.id)

    assert line.are_numbers_self_serve is False
    assert line.self_serve_countries == []
    assert offers.availability is PhoneNumberAvailability.ON_REQUEST
    assert offers.offers == []
    assert world.provisioner.searches == []


def test_the_owner_sees_numbers_at_the_monthly_price_in_lari() -> None:
    world = PhoneWorld()
    owner, _ = world.owner_and_business()

    offers = search(world, owner.id, city="Austin")

    assert offers.availability is PhoneNumberAvailability.SELF_SERVE
    # $1.15 + 30 % = $1.495 at 2.7: 4.04 GEL, rounded up to a whole lari.
    assert offers.monthly_price is not None
    assert int(offers.monthly_price.money.amount_minor) == 500
    assert str(offers.monthly_price.money.currency_code) == "GEL"
    assert [str(offer.display_number) for offer in offers.offers] == [
        "+1 512-555-0142",
        "+1 512-555-0187",
        "+1 512-555-0123",
    ]
    assert {str(offer.locality) for offer in offers.offers} == {"Austin"}
    assert str(world.provisioner.searches[0].city) == "Austin"
    assert int(world.provisioner.searches[0].limit) == 10


def test_a_city_without_numbers_offers_none_at_the_same_price() -> None:
    world = PhoneWorld()
    owner, _ = world.owner_and_business()

    offers = search(world, owner.id, city="Dallas")

    assert offers.availability is PhoneNumberAvailability.SELF_SERVE
    assert offers.offers == []
    assert offers.monthly_price is not None


@pytest.mark.parametrize(
    ("country", "number_type"),
    [
        ("GE", PhoneNumberType.LOCAL),
        ("DE", PhoneNumberType.MOBILE),
        ("US", PhoneNumberType.MOBILE),
        ("FR", PhoneNumberType.LOCAL),
    ],
)
def test_countries_that_want_documents_offer_nothing(
    country: str, number_type: PhoneNumberType
) -> None:
    world = PhoneWorld()
    owner, _ = world.owner_and_business()

    offers = search(world, owner.id, country=country, number_type=number_type)

    assert offers.availability is PhoneNumberAvailability.REQUIRES_DOCUMENTS
    assert offers.offers == []
    assert world.provisioner.searches == []


def test_a_kind_the_carrier_does_not_price_is_arranged_on_request() -> None:
    world = PhoneWorld()
    owner, _ = world.owner_and_business()

    offers = search(world, owner.id, number_type=PhoneNumberType.TOLL_FREE)

    assert offers.availability is PhoneNumberAvailability.ON_REQUEST
    assert offers.offers == []


def test_staff_neither_search_nor_see_more_than_the_line() -> None:
    world = PhoneWorld()
    owner = world.add_user(email="owner@example.com", locale="en")
    staff = world.add_user(email="staff@example.com", locale="en")
    business = world.add_business(owner, staff=[staff])

    line = world.get_line.run(PhoneLineQuery(user_id=staff.id, business_id=business.id))
    assert line.rented_number is None
    with pytest.raises(AccessDeniedError):
        world.search.run(
            PhoneNumberOfferQuery(
                user_id=staff.id,
                business_id=business.id,
                country_code=CountryCode("US"),
                number_type=PhoneNumberType.LOCAL,
            )
        )


def test_a_business_searches_thirty_times_an_hour() -> None:
    world = PhoneWorld()
    owner, _ = world.owner_and_business()

    for _ in range(30):
        search(world, owner.id)
    with pytest.raises(RateLimitedError) as refusal:
        search(world, owner.id)

    assert refusal.value.retry_after_seconds is not None
    assert len(world.provisioner.searches) == 30
