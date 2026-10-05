"""Every business of the platform, walked in keyset batches."""

import pytest

from app.repositories.business_repositories import BusinessRepository
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.businesses.constrained_integers import BusinessBatchSize
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.business_walk import walk_businesses
from tests.storage.builders import COUNTRY_SAMPLES, build_business
from tests.storage.conftest import CollectionFactory

pytestmark = pytest.mark.usefixtures("platform_scope")


def new_business() -> BusinessDocument:
    return build_business(COUNTRY_SAMPLES[0], UserId())


@pytest.mark.parametrize("count", [0, 1, 3, 4, 7])
def test_the_walk_meets_every_business_once_in_creation_order(
    collections: CollectionFactory, count: int
) -> None:
    repo = BusinessRepository(collections(BusinessDocument, "businesses"))
    created = [new_business() for _ in range(count)]
    for business in created:
        repo.save(business)

    walked = list(walk_businesses(repo, BusinessBatchSize(3)))

    assert [business.id for business in walked] == [business.id for business in created]


def test_a_business_created_during_the_walk_is_met_at_its_end(
    collections: CollectionFactory,
) -> None:
    repo = BusinessRepository(collections(BusinessDocument, "businesses"))
    first, second = new_business(), new_business()
    repo.save(first)
    repo.save(second)
    late = new_business()

    walked: list[BusinessId] = []
    for business in walk_businesses(repo, BusinessBatchSize(1)):
        walked.append(business.id)
        if business.id == first.id:
            repo.save(late)

    assert walked == [first.id, second.id, late.id]
