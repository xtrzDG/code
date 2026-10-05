"""
Changes not live yet: what the owner changed in the profile, knowledge,
hours, prices and booking rules since the version customers talk to, the
owner's checks that version was not checked against, and the versions
built since that never went live (drafts).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AssistantVersionStatus,
    AutotestExpectation,
)
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
from app.schemas.typings.assistants.constrained_strings import (
    AutotestCaseQuestion,
    AutotestExpectedText,
)
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestCaseId,
)
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
    autotest_case_id: AutotestCaseId | None = None


class PendingOwnerCheckView(ImmutableDTO):
    """
    One of the owner's checks the live version was not checked against:
    the next "Apply changes" asks it before customers get anything. ADDED
    when the live version was never asked it, CHANGED when the check was
    edited since; with its question, what the answer must do and the
    language it is asked in.
    """

    autotest_case_id: AutotestCaseId
    action: PendingChangeAction
    question: AutotestCaseQuestion
    expectation: AutotestExpectation
    expected_text: AutotestExpectedText | None = None
    language: LanguageTag


class PendingDraftView(ImmutableDTO):
    """
    A version built after the live one that never went live (a preview of
    the test chat, a manual build, an update whose checks failed): its
    customers never saw it, and the owner may discard it.
    """

    assistant_version_id: AssistantVersionId
    version_number: AssistantVersionNumber
    status: AssistantVersionStatus
    created_at: Microseconds


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
    launch. `changes` are what the owner changed in the business,
    `owner_checks` the owner's checks the live version was not checked
    against (a field of their own, so a cabinet that does not know them
    yet lists nothing it cannot name); `count` counts both, which the next
    "Apply changes" takes to customers. `drafts` are the versions built
    since the live one that customers never got.
    """

    business_id: BusinessId
    is_live: IsAssistantLive
    live_version_number: AssistantVersionNumber | None = None
    has_unapplied_changes: HasUnappliedChanges
    count: PendingChangeCount
    changes: list[PendingChange] = Field(default_factory=list[PendingChange])
    owner_checks: list[PendingOwnerCheckView] = Field(
        default_factory=list[PendingOwnerCheckView]
    )
    drafts: list[PendingDraftView] = Field(default_factory=list[PendingDraftView])


class DiscardDraftCommand(ImmutableDTO):
    """The owner discards a draft customers never got."""

    user_id: UserId
    business_id: BusinessId
    assistant_version_id: AssistantVersionId
