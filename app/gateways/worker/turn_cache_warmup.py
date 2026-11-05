"""
What the first customer turn of a worker process would otherwise load, read
before its lanes take jobs: the reply guard's currency symbols of every
CLDR locale and the ISO 4217 codes (`cldr_markers`), about half a second
and a hundred megabytes of locale data that every reply review reads and
the process keeps. Loaded at start, they no longer land on the first
customer answered after each deploy or restart.
"""

import logging
import time

from app.utilities.reply_guard.cldr_markers import (
    load_currency_codes,
    load_currency_symbols,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
MILLISECONDS_PER_SECOND: int = 1_000


def warm_turn_caches() -> None:
    """Load the reply guard's locale-wide markers into their caches."""

    started: float = time.perf_counter()
    load_currency_symbols()
    load_currency_codes()
    LOGGER.info(
        "Reply guard markers loaded in %d ms",
        int((time.perf_counter() - started) * MILLISECONDS_PER_SECOND),
    )
