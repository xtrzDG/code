"""
The rental billing tests that bill play the release after this one, where
the release gate `phone_number_rental` is open (this release reads the kind
`number_rental` but neither stores nor bills it: docs/operations/deploys.md;
test_number_rental_gate.py covers this release).
"""

import pytest

from app.utilities.storage import release_gates
from app.utilities.storage.release_gates import PHONE_NUMBER_RENTAL_GATE


@pytest.fixture
def open_rental_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        release_gates,
        "RELEASE_GATES",
        tuple(
            gate.model_copy(update={"is_open": True})
            if gate.name == PHONE_NUMBER_RENTAL_GATE
            else gate
            for gate in release_gates.RELEASE_GATES
        ),
    )
