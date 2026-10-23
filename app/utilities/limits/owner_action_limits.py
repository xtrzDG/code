"""
Limits on the cabinet actions that make the platform pay a provider: a test
chat message (a model turn) per person, a menu import (a model reading a
menu), an autotest run (hundreds of model turns), a number search (the
carrier's API) and a rented number (its first month) per business. Each is a
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
# StartAutotestRunUseCase). Aliases of one item are asked for while an
# owner edits it: sixty an hour per business (one cheap model call each).
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
    OwnerAction.ALIAS_SUGGESTION: OwnerActionLimit(
        key_prefix="owner-alias-suggestion",
        is_per_person=False,
        limit=60,
        window_seconds=HOUR_SECONDS,
        refusal="Translations can be suggested 60 times an hour; try again later.",
    ),
    # The number picker asks the carrier's API on every search; an owner
    # tries a few cities and kinds. Each rented number costs the platform
    # its first month at once, so taking and giving back numbers in a loop
    # is held at three a day.
    OwnerAction.PHONE_NUMBER_SEARCH: OwnerActionLimit(
        key_prefix="owner-phone-number-search",
        is_per_person=False,
        limit=30,
        window_seconds=HOUR_SECONDS,
        refusal="Numbers can be searched 30 times an hour; try again later.",
    ),
    OwnerAction.PHONE_NUMBER_RENTAL: OwnerActionLimit(
        key_prefix="owner-phone-number-rental",
        is_per_person=False,
        limit=3,
        window_seconds=DAY_SECONDS,
        refusal="A business can take 3 numbers a day; try again tomorrow.",
    ),
    # A request (re)opened e-mails every platform admin: asking, cancelling
    # and asking again in a loop must not flood the team's inbox.
    OwnerAction.PHONE_NUMBER_REQUEST: OwnerActionLimit(
        key_prefix="owner-phone-number-request",
        is_per_person=False,
        limit=3,
        window_seconds=DAY_SECONDS,
        refusal=(
            "A business can ask the team for a number 3 times a day; try again "
            "tomorrow."
        ),
    ),
}
