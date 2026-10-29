"""
Pieces of the profile autosave: niche answers changed one question at a
time, contact phones one number at a time, and the stale-edit refusal.
"""

from collections.abc import Mapping, Sequence

from typed_time_provider import Microseconds

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.constants.businesses import BusinessSettingsRefusalCode
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessContacts, ProfileAnswer
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.niches import NicheTemplate, QuestionDefinition
from app.schemas.dto.profiles.business_profile import (
    ContactsInput,
    ProfileAnswerInput,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.profiles.constrained_strings import QuestionKey
from app.utilities.knowledge.niche_answers import normalize_answer
from app.utilities.knowledge.profile_sections import parse_optional_phone

STALE_PROFILE_MESSAGE: str = (
    "The profile was saved from another window after you opened it. Reload it "
    "and make your change again."
)


def normalize_answer_changes(
    template: NicheTemplate,
    answer_inputs: Sequence[ProfileAnswerInput],
    phone_number_parser: PhoneNumberParserContract,
    business: BusinessDocument,
) -> dict[QuestionKey, ProfileAnswer | None]:
    """
    The canonical answer of every question named (None clears it).

    Raises:
        ValidationFailedError: an unknown question, a question named twice,
            or an answer of the wrong shape.
    """

    questions: dict[QuestionKey, QuestionDefinition] = {
        question.key: question for question in template.questions
    }
    changes: dict[QuestionKey, ProfileAnswer | None] = {}
    for answer_input in answer_inputs:
        question: QuestionDefinition | None = questions.get(answer_input.question_key)
        if question is None:
            raise ValidationFailedError(
                f"Question {answer_input.question_key} does not exist in niche "
                f"{template.key}."
            )

        if question.key in changes:
            raise ValidationFailedError(f"Question {question.key} is answered twice.")

        changes[question.key] = normalize_answer(
            question=question,
            answer_input=answer_input,
            phone_number_parser=phone_number_parser,
            country_code=business.country_code,
        )

    return changes


def apply_answer_changes(
    template: NicheTemplate,
    current_answers: Sequence[ProfileAnswer],
    changes: Mapping[QuestionKey, ProfileAnswer | None],
) -> list[ProfileAnswer]:
    """Answers with only the named questions changed, in question order."""

    current: dict[QuestionKey, ProfileAnswer] = {
        answer.question_key: answer for answer in current_answers
    }
    merged: list[ProfileAnswer] = []
    for question in template.questions:
        answer: ProfileAnswer | None = (
            changes[question.key]
            if question.key in changes
            else current.get(question.key)
        )
        if answer is not None:
            merged.append(answer)

    return merged


def patch_contacts(
    current: BusinessContacts,
    contacts_input: ContactsInput,
    phone_number_parser: PhoneNumberParserContract,
    business: BusinessDocument,
) -> BusinessContacts:
    """The contact phones with only the numbers present in the input changed."""

    provided: set[str] = contacts_input.model_fields_set
    return BusinessContacts(
        public_phone_number=(
            parse_optional_phone(
                contacts_input.public_phone_number, phone_number_parser, business
            )
            if "public_phone_number" in provided
            else current.public_phone_number
        ),
        handoff_phone_number=(
            parse_optional_phone(
                contacts_input.handoff_phone_number, phone_number_parser, business
            )
            if "handoff_phone_number" in provided
            else current.handoff_phone_number
        ),
    )


def build_stale_profile_error(current_updated_at: Microseconds) -> ConflictError:
    """The refusal of an autosave made from an older profile."""

    return ConflictError(
        STALE_PROFILE_MESSAGE,
        reasons=[
            ErrorReason(
                code=ErrorReasonCode(BusinessSettingsRefusalCode.STALE_REVISION.value),
                message=ErrorReasonMessage(STALE_PROFILE_MESSAGE),
                details=[ErrorReasonDetail(str(int(current_updated_at)))],
            )
        ],
    )


def next_revision_time(now: Microseconds, previous: Microseconds) -> Microseconds:
    """
    A save time after the previous one, so `updated_at` works as a revision
    even when two saves land in the same microsecond.
    """

    return Microseconds(max(int(now), int(previous) + 1))
