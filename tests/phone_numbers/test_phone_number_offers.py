"""
A rental takes only a number a search offered this business, as the kind it
offered, within the offer's hour: the kind fixes the price and whether the
regulator wants papers, so the request cannot choose it.
"""

import pytest

from app.schemas.constants.phone_numbers import PhoneNumberType
from app.schemas.dto.phone_numbers.phone_line import (
    PhoneNumberOfferQuery,
    RentPhoneNumberCommand,
    RentPhoneNumberRequest,
)
from app.schemas.dto.phone_numbers.provisioning import PhoneNumberOfferClaims
from app.schemas.exceptions.phone_number_errors import PhoneNumberUnavailableError
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.security.phone_number_offer_signer import PhoneNumberOfferSigner
from tests.phone_numbers.phone_world import AUSTIN_NUMBER, FIVE_LARI, PhoneWorld


def test_a_search_signs_each_offer_for_the_business_and_kind() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()

    found = world.search.run(
        PhoneNumberOfferQuery(
            user_id=owner.id,
            business_id=business.id,
            country_code=CountryCode("US"),
            number_type=PhoneNumberType.LOCAL,
        )
    )

    offer = found.offers[0]
    expires_at = world.offer_signer.read_expiry(offer.offer_token)
    assert expires_at > world.clock.now()
    claims = PhoneNumberOfferClaims(
        business_id=business.id,
        phone_number=offer.phone_number,
        number_type=PhoneNumberType.LOCAL,
        expires_at=expires_at,
    )
    assert world.offer_signer.is_genuine(claims, offer.offer_token)
    toll_free = claims.model_copy(update={"number_type": PhoneNumberType.TOLL_FREE})
    assert not world.offer_signer.is_genuine(toll_free, offer.offer_token)


def test_a_number_declared_as_another_kind_is_refused() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    local_token = world.offer_token(business, AUSTIN_NUMBER, PhoneNumberType.LOCAL)

    with pytest.raises(PhoneNumberUnavailableError, match="not offered"):
        world.rent.run(
            RentPhoneNumberCommand(
                user_id=owner.id,
                business_id=business.id,
                request=RentPhoneNumberRequest(
                    phone_number=AUSTIN_NUMBER,
                    number_type=PhoneNumberType.MOBILE,
                    offer_token=local_token,
                    monthly_price=FIVE_LARI,
                ),
            )
        )

    assert world.provisioner.bought == []


def test_an_offer_to_another_business_or_a_lapsed_one_buys_nothing() -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    _, other = world.owner_and_business("other@example.com")
    request = RentPhoneNumberRequest(
        phone_number=AUSTIN_NUMBER,
        number_type=PhoneNumberType.LOCAL,
        offer_token=world.offer_token(other, AUSTIN_NUMBER),
        monthly_price=FIVE_LARI,
    )
    command = RentPhoneNumberCommand(
        user_id=owner.id, business_id=business.id, request=request
    )
    with pytest.raises(PhoneNumberUnavailableError, match="not offered"):
        world.rent.run(command)

    own = request.model_copy(
        update={"offer_token": world.offer_token(business, AUSTIN_NUMBER)}
    )
    world.clock.advance(hours=1.02)
    with pytest.raises(PhoneNumberUnavailableError, match="lapsed"):
        world.rent.run(command.model_copy(update={"request": own}))

    assert world.provisioner.bought == []


def test_an_offer_signed_before_a_key_rotation_still_holds() -> None:
    world = PhoneWorld()
    _, business = world.owner_and_business()
    old = PhoneNumberOfferSigner(PlatformSecret("old-key-0000"))
    rotated = PhoneNumberOfferSigner(
        PlatformSecret("new-key-0000"), [PlatformSecret("old-key-0000")]
    )
    claims = PhoneNumberOfferClaims(
        business_id=business.id,
        phone_number=AUSTIN_NUMBER,
        number_type=PhoneNumberType.LOCAL,
        expires_at=world.clock.now(),
    )
    token = old.sign(claims)
    signed_claims = claims.model_copy(update={"expires_at": old.read_expiry(token)})

    assert rotated.is_genuine(signed_claims, token)
    assert not PhoneNumberOfferSigner(PlatformSecret("new-key-0000")).is_genuine(
        signed_claims, token
    )
