"""
The lifecycle tests play the release after this one, where the release
gate of the `paused` status is open: this release reads the value but
neither stores nor offers it (docs/operations/deploys.md;
tests/storage/test_subscription_pause_gate.py covers this release).
"""

import pytest

from app.utilities.storage import release_gates
from app.utilities.storage.release_gates import SUBSCRIPTION_PAUSE_GATE


@pytest.fixture(autouse=True)
def open_subscription_pause_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        release_gates,
        "RELEASE_GATES",
        tuple(
            gate.model_copy(update={"is_open": True})
            if gate.name == SUBSCRIPTION_PAUSE_GATE
            else gate
            for gate in release_gates.RELEASE_GATES
        ),
    )
