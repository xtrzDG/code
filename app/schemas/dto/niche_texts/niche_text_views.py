"""What the platform admin's niche template editor shows."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.niches import (
    NicheKey,
    NicheTextReleaseKind,
    NicheTextSection,
    ProfileWizardStep,
    QuestionAnswerType,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.schemas.typings.niches.booleans import (
    HasUnpublishedNicheTexts,
    IsQuestionRequired,
)
from app.schemas.typings.niches.constrained_integers import (
    NicheOverrideCount,
    NicheTextLengthLimit,
    NicheTextVersion,
)
from app.schemas.typings.niches.constrained_strings import (
    NicheOverrideText,
    NicheTextFieldKey,
)
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey,
    QuestionKey,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName


class NicheTextStatusView(ImmutableDTO):
    """
    A niche's override state: the published version (0: the code template,
    nothing overridden) with how many texts it replaces, when and by whom
    it was published, and whether a draft waits to be published.
    """

    niche_key: NicheKey
    name: LocalizedTextValue
    published_version: NicheTextVersion
    override_count: NicheOverrideCount
    published_at: Microseconds | None = None
    published_by_name: UserDisplayName | None = None
    has_draft: HasUnpublishedNicheTexts
    draft_override_count: NicheOverrideCount


class NicheTextStatusList(ImmutableDTO):
    """Every niche, in the order of the concept's niche table."""

    language: LanguageTag
    items: list[NicheTextStatusView] = Field(default_factory=list[NicheTextStatusView])


class NicheTextFieldView(ImmutableDTO):
    """
    One editable text in the editor's language: the code's text (None when
    the code has none in this language, so owners read English), the
    English code text, the published and the draft wording (None: no
    override) and the longest wording allowed.
    """

    field_key: NicheTextFieldKey
    section: NicheTextSection
    question_key: QuestionKey | None = None
    code_text: LocalizedTextValue | None = None
    english_text: LocalizedTextValue
    published_text: NicheOverrideText | None = None
    draft_text: NicheOverrideText | None = None
    max_length: NicheTextLengthLimit


class NicheTextChoiceView(ImmutableDTO):
    """A choice of a question: its editable field, or a fixed platform label."""

    key: QuestionChoiceKey
    field_key: NicheTextFieldKey | None = None
    fixed_label: LocalizedTextValue | None = None


class NicheTextQuestionView(ImmutableDTO):
    """A profile question as the preview lays it out (structure from code)."""

    key: QuestionKey
    step: ProfileWizardStep
    answer_type: QuestionAnswerType
    is_required: IsQuestionRequired
    label_field: NicheTextFieldKey
    hint_field: NicheTextFieldKey | None = None
    choices: list[NicheTextChoiceView] = Field(
        default_factory=list[NicheTextChoiceView]
    )


class NicheTextEditorView(ImmutableDTO):
    """The editor of one niche in one of the cabinet's languages."""

    niche_key: NicheKey
    language: LanguageTag
    languages: list[LanguageTag]
    status: NicheTextStatusView
    fields: list[NicheTextFieldView]
    questions: list[NicheTextQuestionView]


class NicheTextReleaseView(ImmutableDTO):
    """
    A published version: what made it (publish, revert, reset), how many
    texts it replaces, the version a revert went back to, when and by whom.
    """

    niche_key: NicheKey
    version: NicheTextVersion
    kind: NicheTextReleaseKind
    override_count: NicheOverrideCount
    restored_version: NicheTextVersion | None = None
    published_at: Microseconds
    published_by: UserId
    published_by_name: UserDisplayName | None = None


class NicheTextHistoryView(ImmutableDTO):
    """A niche's published versions, newest first (version 0 is the code)."""

    niche_key: NicheKey
    items: list[NicheTextReleaseView] = Field(
        default_factory=list[NicheTextReleaseView]
    )
