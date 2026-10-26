"""The editable texts of one niche template, as the code defines them."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.niches import (
    NicheKey,
    NicheTextSection,
    ProfileWizardStep,
    QuestionAnswerType,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.niches.booleans import IsQuestionRequired
from app.schemas.typings.niches.constrained_integers import NicheTextLengthLimit
from app.schemas.typings.niches.constrained_strings import NicheTextFieldKey
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey,
    QuestionKey,
)


class NicheTextField(ImmutableDTO):
    """
    One owner-facing text of a niche template an admin may reword: its key,
    where it belongs (and to which question), the code's own text in every
    language that has one, and the longest wording its use accepts.
    """

    field_key: NicheTextFieldKey
    section: NicheTextSection
    question_key: QuestionKey | None = None
    code_texts: LocalizedText
    max_length: NicheTextLengthLimit


class NicheTextChoice(ImmutableDTO):
    """
    A predefined answer of a question: editable through `field_key`, or a
    platform-wide label (the common yes and no) that the niche cannot change.
    """

    key: QuestionChoiceKey
    field_key: NicheTextFieldKey | None = None
    fixed_labels: LocalizedText | None = None


class NicheTextQuestion(ImmutableDTO):
    """A profile question's structure (fixed in code) and its editable texts."""

    key: QuestionKey
    step: ProfileWizardStep
    answer_type: QuestionAnswerType
    is_required: IsQuestionRequired
    label_field: NicheTextFieldKey
    hint_field: NicheTextFieldKey | None = None
    choices: list[NicheTextChoice] = Field(default_factory=list[NicheTextChoice])


class NicheTextCatalog(ImmutableDTO):
    """Every editable text of a niche and the questions they belong to."""

    niche_key: NicheKey
    fields: list[NicheTextField]
    questions: list[NicheTextQuestion]
