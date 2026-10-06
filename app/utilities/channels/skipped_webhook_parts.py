"""
What a verified webhook carried besides customer messages, for the logs.

Channel adapters skip delivery receipts, echoes, edits, reactions and
kinds of events they do not know; the log line names the kinds, so a new
variant of a platform's webhook shows up in the logs instead of silence,
and never as an error. Only labels from the adapters' known lists and
counts are written, nothing of the body itself: an unknown kind reads
"other".
"""

import logging
from collections import Counter
from collections.abc import Collection, Sequence

OTHER_KIND: str = "other"


def known_kind(raw_kind: object, known_kinds: Collection[str]) -> str:
    """The adapter's own label for a kind it knows, else "other"."""

    labels: dict[str, str] = {kind: kind for kind in known_kinds}
    return labels.get(raw_kind, OTHER_KIND) if isinstance(raw_kind, str) else OTHER_KIND


def log_skipped_parts(
    logger: logging.Logger,
    platform: str,
    kinds: Sequence[str],
    routine_kinds: Collection[str] = frozenset(),
) -> None:
    """
    One line per delivery: DEBUG when every kind is routine (receipts of
    the platform's own messages), INFO when something else was skipped.
    """

    if not kinds:
        return

    counts: Counter[str] = Counter(kinds)
    is_routine: bool = all(kind in routine_kinds for kind in counts)
    logger.log(
        logging.DEBUG if is_routine else logging.INFO,
        "%s webhook: skipped %d part(s) without a customer message: %s.",
        platform,
        len(kinds),
        ", ".join(f"{kind}={count}" for kind, count in sorted(counts.items())),
    )
