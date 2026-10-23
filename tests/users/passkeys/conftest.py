"""Fixtures of the passkey tests: a workshop whose cabinet is CABINET_ORIGIN."""

from collections.abc import Iterator

import pytest

from tests.e2e.harness import Workshop, start_workshop
from tests.e2e.harness_settings import CABINET_ORIGIN, E2E_ENVIRONMENT


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    workshop = start_workshop({**E2E_ENVIRONMENT, "CABINET_BASE_URL": CABINET_ORIGIN})
    with workshop.client:
        yield workshop
