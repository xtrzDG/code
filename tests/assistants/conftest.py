"""Fixtures of updates and the owner's checks: a workshop on the rehearsal model."""

from collections.abc import Iterator

import pytest

from tests.e2e.harness import Workshop
from tests.pending_changes.rehearsal_workshop import start_rehearsal_workshop


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    workshop = start_rehearsal_workshop()
    with workshop.client:
        yield workshop
