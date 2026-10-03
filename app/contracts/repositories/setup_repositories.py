"""
Persistence contracts of the guided launch: milestones, setup state, the
current "Apply changes", and the probes that notice a business's first
real conversation, booking and handoff.

Implementations return independent copies: mutating a returned document
does not change stored state until it is saved. Every document is looked
up through its business id, so one tenant never sees another's data.
"""

from collections.abc import Callable
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.setup import ActivationEventKind
from app.schemas.constants.nudges import NudgeCode
from app.schemas.domain.setup import (
    ActivationEventDocument,
    AssistantApplyDocument,
    NudgeSentDocument,
    SetupStateDocument,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ChannelUserId


class ActivationEventRepoContract(RepoContract, Protocol):
    def record_once(self, event: ActivationEventDocument) -> bool:
        """
        Store a milestone unless its business already has one of that kind
        (atomic, also across processes); True when it was stored now.
        """
        raise NotImplementedError

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[ActivationEventDocument]:
        """The milestones of a business, oldest first."""
        raise NotImplementedError

    def mark_celebrated(
        self,
        business_id: BusinessId,
        kind: ActivationEventKind,
        celebrated_at: Microseconds,
    ) -> ActivationEventDocument | None:
        """
        Note that the cabinet showed the milestone (the first time only);
        None when the business has not reached it.
        """
        raise NotImplementedError


class SetupStateRepoContract(RepoContract, Protocol):
    def get_by_business(self, business_id: BusinessId) -> SetupStateDocument | None:
        raise NotImplementedError

    def change(
        self,
        business_id: BusinessId,
        apply: Callable[[SetupStateDocument], None],
        now: Microseconds,
    ) -> SetupStateDocument:
        """
        Change the setup state of a business as stored now, in one step
        (an empty state is created first when there is none).
        """
        raise NotImplementedError


class AssistantApplyRepoContract(RepoContract, Protocol):
    def get_by_business(self, business_id: BusinessId) -> AssistantApplyDocument | None:
        raise NotImplementedError

    def save(self, apply: AssistantApplyDocument) -> None:
        raise NotImplementedError

    def insert_if_absent(self, apply: AssistantApplyDocument) -> bool:
        """Store the first apply of a business (atomic); False when one exists."""
        raise NotImplementedError

    def modify(
        self,
        business_id: BusinessId,
        change: Callable[[AssistantApplyDocument], AssistantApplyDocument | None],
    ) -> AssistantApplyDocument | None:
        """
        Store what `change` makes of the business's apply as stored now, in
        one step; None, and nothing written, when there is no apply or
        `change` returns None.
        """
        raise NotImplementedError


class ActivationProbeRepoContract(RepoContract, Protocol):
    """
    When a business first had something real (not the test chat or the
    automatic checks). Each probe reads a bounded number of the business's
    earliest documents through the business index, never its whole history.
    """

    def find_first_real_conversation_at(
        self, business_id: BusinessId
    ) -> Microseconds | None:
        raise NotImplementedError

    def find_first_real_booking_at(
        self, business_id: BusinessId
    ) -> Microseconds | None:
        raise NotImplementedError

    def find_first_real_handoff_at(
        self, business_id: BusinessId
    ) -> Microseconds | None:
        raise NotImplementedError


class NudgeSentRepoContract(RepoContract, Protocol):
    def find(self, business_id: BusinessId, code: NudgeCode) -> NudgeSentDocument | None:
        """The nudge of this code the business was sent, if any."""
        raise NotImplementedError

    def record_once(self, nudge: NudgeSentDocument) -> bool:
        """
        Store a sent nudge unless the business already has one of that code
        (atomic, also across processes); True when it was stored now.
        """
        raise NotImplementedError


class SetupProbeRepoContract(RepoContract, Protocol):
    """
    What the guide after the launch notices in a business's own records,
    reading a bounded number of documents through indexes: a message from
    the owner's own phone, and the first booking made while closed.
    """

    def find_first_conversation_from(
        self,
        business_id: BusinessId,
        channel_user_ids: frozenset[ChannelUserId],
    ) -> Microseconds | None:
        """When the first real conversation with one of these senders began."""
        raise NotImplementedError

    def find_first_conversation_between(
        self,
        business_id: BusinessId,
        since: Microseconds,
        until: Microseconds,
    ) -> Microseconds | None:
        """When the first real conversation within the window began."""
        raise NotImplementedError

    def find_first_after_hours_booking_at(
        self, business_id: BusinessId
    ) -> Microseconds | None:
        """When the first real booking from a conversation after hours was made."""
        raise NotImplementedError
