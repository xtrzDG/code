"""
Taking a number while a platform brake holds (the global pause, the daily
budget stop): refused before the carrier is asked, so nothing is bought;
a brake that starts while the carrier sells the number does not lose it,
the number is recorded and counted like any other.
"""

from dataclasses import dataclass, field

import pytest

from app.schemas.constants.phone_numbers import PhoneNumberStatus
from app.schemas.constants.spend import PlatformBrake
from app.schemas.dto.phone_numbers.provisioning import (
    PhoneNumberPurchase,
    ProvisionedPhoneNumber,
)
from app.schemas.exceptions.application_errors import ConflictError
from tests.phone_numbers.phone_world import AUSTIN_NUMBER, PhoneWorld
from tests.phone_numbers.provisioner_fakes import FakePhoneNumberProvisioner
from tests.spend_guard.platform_brake_fakes import SetPlatformBrakes


@dataclass
class BrakeDuringPurchase(FakePhoneNumberProvisioner):
    """A carrier during whose sale a platform brake starts."""

    brakes: SetPlatformBrakes = field(default_factory=SetPlatformBrakes)

    def buy_number(self, purchase: PhoneNumberPurchase) -> ProvisionedPhoneNumber:
        provisioned = super().buy_number(purchase)
        self.brakes.brake = PlatformBrake.BUDGET_STOP
        return provisioned


@pytest.mark.parametrize("brake", list(PlatformBrake))
def test_a_number_is_not_bought_while_a_brake_holds(brake: PlatformBrake) -> None:
    world = PhoneWorld()
    owner, business = world.owner_and_business()
    world.platform_brakes.brake = brake

    with pytest.raises(ConflictError) as refusal:
        world.rent_austin_number(owner, business)

    [reason] = refusal.value.reasons
    assert (str(reason.code), [str(detail) for detail in reason.details]) == (
        "platform_brake",
        [brake.value],
    )
    assert world.provisioner.bought == []
    assert world.phone_number_repo.find_held(business.id) is None


def test_a_brake_starting_during_the_sale_keeps_the_bought_number() -> None:
    carrier = BrakeDuringPurchase()
    world = PhoneWorld(provisioner=carrier)
    carrier.brakes = world.platform_brakes
    owner, business = world.owner_and_business()

    world.rent_austin_number(owner, business)

    number = world.rented(business)
    assert (str(number.phone_number), number.status) == (
        str(AUSTIN_NUMBER),
        PhoneNumberStatus.ACTIVE,
    )
    assert [str(bought.phone_number) for bought in carrier.bought] == [
        str(AUSTIN_NUMBER)
    ]
    assert world.platform_brakes.brake is PlatformBrake.BUDGET_STOP
