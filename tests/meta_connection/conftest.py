"""Fixtures of the Meta connection tests."""

import pytest

from app.utilities.storage import release_gates
from tests.meta_connection.comment_world import opened_gates


@pytest.fixture
def next_release(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Stand in the next release: the comment-replies gate is open, for storage
    built afterwards and for the use cases (the gates are read when asked).
    """

    monkeypatch.setattr(release_gates, "RELEASE_GATES", opened_gates())
