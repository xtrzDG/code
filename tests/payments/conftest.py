"""
The Stripe tests play the release after this one, where the release gate of
the `stripe` provider value is open (this release reads Stripe rows but
neither stores them nor routes owners to Stripe; the registry tests cover
the closed gate).
"""

import pytest

from app.utilities.storage import release_gates
from app.utilities.storage.release_gates import STRIPE_PAYMENTS_GATE


@pytest.fixture
def stripe_gate_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        release_gates,
        "RELEASE_GATES",
        tuple(
            gate.model_copy(update={"is_open": True})
            if gate.name == STRIPE_PAYMENTS_GATE
            else gate
            for gate in release_gates.RELEASE_GATES
        ),
    )
