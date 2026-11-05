"""A started workshop whose cabinet address is known (the referral links)."""

from collections.abc import Iterator

import pytest

from tests.e2e.harness import Workshop, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.referrals.referral_workshop import CABINET_BASE_URL


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    workshop = start_workshop({**E2E_ENVIRONMENT, "CABINET_BASE_URL": CABINET_BASE_URL})
    with workshop.client:
        yield workshop
