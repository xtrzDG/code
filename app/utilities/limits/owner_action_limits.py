"""
Limits on the cabinet actions that make the platform pay a provider: a test
chat message (a model turn) per person, a menu import (a model reading a
menu) and an autotest run (hundreds of model turns) per business. Each is a
sliding window over the shared request counters, so every API instance
counts against the same limit; a refusal is a 429 with Retry-After.
"""

from dataclasses import dataclass

from app.schemas.constants.spend import OwnerAction


@dataclass(frozen=True)
class OwnerActionLimit:
    """At most `limit` actions per window, per person or per business."""

    key_prefix: str
    is_per_person: bool
    limit: int
    window_seconds: int
    refusal: str


MINUTE_SECONDS: int = 60
HOUR_SECONDS: int = 60 * 60
DAY_SECONDS: int = 24 * 60 * 60
# A person tries an answer every few seconds at most; a script that loops
# the test chat is held at 30 model turns a minute. A menu is imported a
# few times while an owner fixes it; ten an hour is plenty. Autotests run
# after each change: twenty a day per business (one at a time, see
# StartAutotestRunUseCase).
OWNER_ACTION_LIMITS: dict[OwnerAction, OwnerActionLimit] = {
    OwnerAction.TEST_CHAT: OwnerActionLimit(
        key_prefix="owner-test-chat",
        is_per_person=True,
        limit=30,
        window_seconds=MINUTE_SECONDS,
        refusal="Too many test messages in a minute; wait a moment.",
    ),
    OwnerAction.MENU_IMPORT: OwnerActionLimit(
        key_prefix="owner-menu-import",
        is_per_person=False,
        limit=10,
        window_seconds=HOUR_SECONDS,
        refusal="A menu can be imported 10 times an hour; try again later.",
    ),
    OwnerAction.AUTOTEST_RUN: OwnerActionLimit(
        key_prefix="owner-autotest-run",
        is_per_person=False,
        limit=20,
        window_seconds=DAY_SECONDS,
        refusal="Autotests can run 20 times a day; try again tomorrow.",
    ),
}
