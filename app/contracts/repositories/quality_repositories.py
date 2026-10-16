"""
Persistence contracts of production quality: the judge's scores of real
conversations (one per conversation), the platform's totals of them (the
nightly budget, the QUALITY_DROP alert) and the conversations the nightly
sample is drawn from.
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.platform_health import ActivityWindow
from app.schemas.dto.quality import QualityTotals
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)


class ConversationQualityRepoContract(RepoContract, Protocol):
    def get(
        self, business_id: BusinessId, conversation_id: ConversationId
    ) -> ConversationQualityScoreDocument | None:
        """The conversation's score; None when it was never judged."""
        raise NotImplementedError

    def save(self, score: ConversationQualityScoreDocument) -> None:
        raise NotImplementedError

    def sum_days(
        self,
        business_id: BusinessId,
        day_starts: Sequence[Microseconds],
        until: Microseconds,
    ) -> list[QualityTotals]:
        """
        The business's scores per day, counted by the database: entry i
        covers `day_starts[i]` up to the next start (the last one up to
        `until`).
        """
        raise NotImplementedError

    def list_lowest(
        self,
        business_id: BusinessId,
        window: ActivityWindow,
        limit: DocumentQueryLimit,
    ) -> list[ConversationQualityScoreDocument]:
        """The business's lowest scores judged in the window, lowest first."""
        raise NotImplementedError


class QualityTotalsRepoContract(RepoContract, Protocol):
    """Platform-wide reads and the retention purge (platform operators)."""

    def sum_judged(self, window: ActivityWindow) -> QualityTotals:
        """Every business's scores judged in the window, summed."""
        raise NotImplementedError

    def delete_judged_before(self, cutoff: Microseconds) -> DocumentCount:
        """Delete the scores judged before `cutoff`; how many."""
        raise NotImplementedError


class QualitySampleInputRepoContract(RepoContract, Protocol):
    def list_recent(
        self,
        business_id: BusinessId,
        window: ActivityWindow,
        limit: DocumentQueryLimit,
    ) -> list[ConversationDocument]:
        """
        The business's conversations (sandbox left out) whose last message
        is in the window, newest first.
        """
        raise NotImplementedError
