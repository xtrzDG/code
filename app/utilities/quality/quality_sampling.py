"""
Which real conversations the nightly quality sampling judges, in which
order, and what it may spend.

A conversation is in the sample when a hash of its id falls in the first
QUALITY_SAMPLE_PERCENT of 100 buckets: the choice is stable (a retried
run picks the same conversations) and needs no stored state. Businesses
take turns (one conversation of each, then the next of each), so the
night's budget is not spent on the first businesses alone.
"""

import hashlib
from collections.abc import Sequence
from uuid import UUID, uuid5

from typed_time_provider import Microseconds

from app.schemas.domain.assistants import JudgeCriterionScore
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.quality.constrained_integers import (
    ConversationQualityHundredths,
    QualitySampleBudgetCents,
    QualitySamplePercent,
)
from app.schemas.typings.quality.prefixed_id import ConversationQualityScoreId

SAMPLE_BUCKETS: int = 100
MICRO_USD_PER_CENT: int = 10_000
MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
HUNDREDTHS: int = 100
# Fixed namespace of derived score ids (never change it: stored ids depend
# on it, and a conversation already judged is found by its id).
QUALITY_SCORE_NAMESPACE: UUID = UUID("3c75aa72-8b1d-4b66-9490-44f61c1c4bf1")


def quality_score_id_of(conversation_id: ConversationId) -> ConversationQualityScoreId:
    """One score per conversation."""

    return ConversationQualityScoreId(
        uuid5(QUALITY_SCORE_NAMESPACE, str(conversation_id))
    )


def is_sampled(conversation_id: ConversationId, percent: QualitySamplePercent) -> bool:
    """True for about `percent` of all conversations, always the same ones."""

    digest: bytes = hashlib.sha256(f"quality|{conversation_id}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % SAMPLE_BUCKETS < int(percent)


def take_turns[Item](groups: Sequence[Sequence[Item]]) -> list[Item]:
    """The first item of every group, then the second of every group, ..."""

    longest: int = max((len(group) for group in groups), default=0)
    return [
        group[position]
        for position in range(longest)
        for group in groups
        if position < len(group)
    ]


def budget_micro_usd(cents: QualitySampleBudgetCents) -> int:
    return int(cents) * MICRO_USD_PER_CENT


def utc_day_start(now: Microseconds) -> Microseconds:
    """Midnight UTC of the day `now` falls in (the budget's day)."""

    return Microseconds(int(now) - int(now) % MICROSECONDS_PER_DAY)


def to_hundredths(
    scores: Sequence[JudgeCriterionScore],
) -> ConversationQualityHundredths:
    """The average score in hundredths of a point, rounded half up."""

    total: int = sum(int(score.score) for score in scores)
    return ConversationQualityHundredths(
        (total * HUNDREDTHS * 2 + len(scores)) // (len(scores) * 2)
    )
