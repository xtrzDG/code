"""A started workshop whose cabinet address is known (the manage links)."""

from collections.abc import Iterator

import pytest

from tests.e2e.harness import Workshop, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT

CABINET_BASE_URL: str = "https://app.workshop.example"


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    workshop = start_workshop({**E2E_ENVIRONMENT, "CABINET_BASE_URL": CABINET_BASE_URL})
    with workshop.client:
        yield workshop
