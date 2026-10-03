"""
Changes not live yet: what the owner changed in the profile, knowledge,
hours, prices and booking rules since the version customers talk to.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.businesses import BusinessLinkKind, Weekday
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.setup import (
    PendingChangeAction,
    PendingChangeArea,
    PendingChangeDetail,
    PendingChangeField,
)
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.setup.booleans import HasUnappliedChanges, IsAssistantLive
from app.schemas.typings.setup.constrained_integers import PendingChangeCount
from app.schemas.typings.setup.strings import PendingChangeSubject, PendingChangeValue
from app.schemas.typings.users.prefixed_id import UserId


class PendingChange(ImmutableDTO):
    """
    One change customers do not get yet, typed so the cabinet can say it in
    the owner's language: the `area` and the `action`, and what it is about
    (one of `field`, `weekday`, `link_kind`, `date` or the owner's own
    words in `subject`, with the `item_kind` of an offer item or
    question). A changed price of an offer item has `detail` PRICE with the
    prices `before` and `after` as the assistant states them.
    """

    area: PendingChangeArea
    action: PendingChangeAction
    field: PendingChangeField | None = None
    weekday: Weekday | None = None
    link_kind: BusinessLinkKind | None = None
    date: LocalDate | None = None
    item_kind: KnowledgeItemKind | None = None
    subject: PendingChangeSubject | None = None
    detail: PendingChangeDetail | None = None
    before: PendingChangeValue | None = None
    after: PendingChangeValue | None = None


class PendingChangesQuery(ImmutableDTO):
    """Read the changes not live yet (niche question labels in `language`)."""

    user_id: UserId
    business_id: BusinessId
    language: LanguageTag | None = None


class PendingChangesRequest(ImmutableDTO):
    """
    Compare what the assistant would be built from now with `version`
    (the live one, or the latest one an apply could reuse); niche
    question labels in `language`.
    """

    business: BusinessDocument
    version: AssistantVersionDocument
    language: LanguageTag


class PendingChangesView(ImmutableDTO):
    """
    The changes customers do not get yet. Before the first go-live there is
    nothing to compare with: `is_live` is False and `changes` is empty,
    while `has_unapplied_changes` says whether there is a profile to
    launch.
    """

    business_id: BusinessId
    is_live: IsAssistantLive
    live_version_number: AssistantVersionNumber | None = None
    has_unapplied_changes: HasUnappliedChanges
    count: PendingChangeCount
    changes: list[PendingChange] = Field(default_factory=list[PendingChange])
