"""
A brand pays one setup fee: when its locations' first invoices are issued
at the same moment, exactly one location claims the fee, in memory and on
Postgres, and every later claim names that same location.
"""

import threading

from app.repositories.brand_repositories import BrandRepository
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.domain.brands import BrandDocument, BrandMember
from app.schemas.typings.brands.strings import BrandName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from tests.storage.concurrency_limits import THREAD_COUNT
from tests.storage.conftest import CollectionFactory


def build_brand() -> BrandDocument:
    return BrandDocument(
        name=BrandName("Mtsvane Ezo"),
        members=[BrandMember(user_id=UserId(), role=BrandMemberRole.BRAND_OWNER)],
    )


def test_locations_racing_for_the_setup_fee_leave_one_holder(
    collections: CollectionFactory,
) -> None:
    repo = BrandRepository(collections(BrandDocument, "brands"))
    brand = build_brand()
    repo.add(brand)
    locations = [BusinessId() for _ in range(THREAD_COUNT)]
    start = threading.Barrier(THREAD_COUNT)
    claimed: dict[BusinessId, bool] = {}
    errors: list[BaseException] = []
    lock = threading.Lock()

    def claim(location: BusinessId) -> None:
        try:
            start.wait()
            won = repo.claim_setup_fee(brand.id, location)
            with lock:
                claimed[location] = won
        except BaseException as error:  # pragma: no cover - reported below
            errors.append(error)

    threads = [threading.Thread(target=claim, args=(item,)) for item in locations]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    winners = [location for location, won in claimed.items() if won]
    assert len(winners) == 1
    stored = repo.get(brand.id)
    assert stored is not None
    assert stored.setup_fee_business_id == winners[0]
    # The holder keeps it; everyone else is refused, again and again.
    assert repo.claim_setup_fee(brand.id, winners[0]) is True
    assert not any(
        repo.claim_setup_fee(brand.id, location)
        for location in locations
        if location != winners[0]
    )


def test_a_missing_brand_gives_no_claim(collections: CollectionFactory) -> None:
    repo = BrandRepository(collections(BrandDocument, "brands"))

    assert repo.claim_setup_fee(build_brand().id, BusinessId()) is False
