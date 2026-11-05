"""
The "what to add" list: gaps in the profile the assistant needs filled.

Display texts (labels, hints, titles) are resolved to one language for the
caller: requested tag, then its base language, then English.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.constants.profiles import ProfileGapKind
from app.schemas.typings.assistants.strings import GapDescription
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.constrained_integers import QuestionOccurrenceCount
from app.schemas.typings.handoffs.prefixed_id import UnansweredQuestionId
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.profiles.booleans import IsProfileGapBlocking, IsProfileReady
from app.schemas.typings.profiles.constrained_strings import QuestionKey


class ProfileGapsQuery(ImmutableDTO):
    """The "what to add" list in `language` (owner language when None)."""

    business_id: BusinessId
    language: LanguageTag | None = None


class ProfileGapFinding(ImmutableDTO):
    """A gap found in the profile data, before it is worded for the owner."""

    kind: ProfileGapKind
    step: ProfileWizardStep
    is_blocking: IsProfileGapBlocking
    question_key: QuestionKey | None = None


class ProfileGap(ImmutableDTO):
    """
    One item of the "what to add" list.

    Blocking gaps stop the assistant from being assembled; the others make it
    answer better.
    """

    kind: ProfileGapKind
    step: ProfileWizardStep
    is_blocking: IsProfileGapBlocking
    description: GapDescription
    question_key: QuestionKey | None = None
    unanswered_question_id: UnansweredQuestionId | None = None
    unanswered_question: UnansweredQuestionText | None = None
    occurrence_count: QuestionOccurrenceCount | None = None


class ProfileGapsView(ImmutableDTO):
    """Blocking gaps first, then advice, then customers' unanswered questions."""

    business_id: BusinessId
    language: LanguageTag
    gaps: list[ProfileGap] = Field(default_factory=list[ProfileGap])
    is_ready_for_assembly: IsProfileReady
