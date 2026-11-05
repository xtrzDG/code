"""
Two clicks never rent two numbers: the phone line lock serializes them.

The first rental is held inside the carrier's purchase until the second
one is at the lock; without the lock the second would pass every check
(nothing is stored yet) and buy a second number.
"""

import threading
from collections.abc import Generator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.contracts.phone_numbers import PhoneLineLockRegistryContract
from app.registries.locks.phone_line_lock_registry import PhoneLineLockRegistry
from app.schemas.dto.phone_numbers.provisioning import (
    PhoneNumberPurchase,
    ProvisionedPhoneNumber,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from tests.phone_numbers.phone_world import PhoneWorld
from tests.phone_numbers.provisioner_fakes import (
    AUSTIN_NUMBERS,
    FakePhoneNumberProvisioner,
)

WAIT_SECONDS: float = 10.0


@dataclass
class HeldPurchase(FakePhoneNumberProvisioner):
    """A carrier whose first purchase waits until the test lets it finish."""

    buying: threading.Event = field(default_factory=threading.Event)
    finish: threading.Event = field(default_factory=threading.Event)

    def buy_number(self, purchase: PhoneNumberPurchase) -> ProvisionedPhoneNumber:
        self.buying.set()
        assert self.finish.wait(WAIT_SECONDS)
        return super().buy_number(purchase)


class ArrivalsAtTheLock(PhoneLineLockRegistryContract):
    """The real lock, telling the test each time a rental reaches it."""

    def __init__(self, inner: PhoneLineLockRegistryContract) -> None:
        self.inner: PhoneLineLockRegistryContract = inner
        self.arrivals: list[threading.Event] = [threading.Event(), threading.Event()]
        self._count: int = 0
        self._guard = threading.Lock()

    def lock_for(self, business_id: BusinessId) -> AbstractContextManager[object]:
        return self._arrive_then_hold(business_id)

    @contextmanager
    def _arrive_then_hold(self, business_id: BusinessId) -> Generator[object]:
        with self._guard:
            arrival = self.arrivals[self._count]
            self._count += 1
        arrival.set()
        with self.inner.lock_for(business_id) as held:
            yield held


def test_two_rentals_at_once_buy_one_number() -> None:
    carrier = HeldPurchase()
    lock = ArrivalsAtTheLock(PhoneLineLockRegistry(InMemoryAdvisoryLockAdapter()))
    world = PhoneWorld(provisioner=carrier, phone_line_lock=lock)
    owner, business = world.owner_and_business()
    outcomes: dict[str, object] = {}

    def rent(name: str, phone_number: str) -> None:
        try:
            outcomes[name] = world.rent_austin_number(
                owner, business, phone_number=E164PhoneNumber(phone_number)
            )
        except ConflictError as refusal:
            outcomes[name] = refusal

    first = threading.Thread(target=rent, args=("first", AUSTIN_NUMBERS[0]))
    first.start()
    assert carrier.buying.wait(WAIT_SECONDS)
    second = threading.Thread(target=rent, args=("second", AUSTIN_NUMBERS[1]))
    second.start()
    # The second rental is at the lock while the first is still buying.
    assert lock.arrivals[1].wait(WAIT_SECONDS)
    assert carrier.bought == []
    carrier.finish.set()
    first.join(WAIT_SECONDS)
    second.join(WAIT_SECONDS)

    assert not isinstance(outcomes["first"], ConflictError)
    assert isinstance(outcomes["second"], ConflictError)
    assert "already has a number" in str(outcomes["second"])
    assert [str(bought.phone_number) for bought in carrier.bought] == [
        AUSTIN_NUMBERS[0]
    ]
    assert str(world.rented(business).phone_number) == AUSTIN_NUMBERS[0]
