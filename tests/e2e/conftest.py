"""Fixtures of the end-to-end journeys: a started workshop (see harness.py)."""

from collections.abc import Iterator

import pytest

from tests.e2e.harness import Workshop, start_workshop


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    workshop = start_workshop()
    with workshop.client:
        yield workshop
