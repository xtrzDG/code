"""Validation of answers to niche-specific profile questions.

Answers are stored as text facts in a canonical form:
- numbers as ASCII digits (digits of any script are accepted, e.g. "٣٠");
- yes/no as "yes" or "no";
- choices as their keys, several keys joined with commas;
- links as absolute http(s) URLs;
- phone numbers in E.164, parsed with the business country as a hint.
"""

from collections.abc import Sequence

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.schemas.constants.niches import ProfileWizardStep, QuestionAnswerType
from app.schemas.domain.profiles import ProfileAnswer
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.dto.niches import NicheTemplate, QuestionDefinition
from app.schemas.dto.profiles.business_profile import ProfileAnswerInput
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey,
    QuestionKey,
)
from app.schemas.typings.profiles.strings import ProfileAnswerText

CHOICE_SEPARATOR: str = ","
YES_KEY: str = "yes"
NO_KEY: str = "no"
MAX_SHORT_TEXT_LENGTH: int = 300
MAX_LONG_TEXT_LENGTH: int = 4000


def merge_niche_answers(
    template: NicheTemplate,
    current_answers: Sequence[ProfileAnswer],
    answer_inputs: Sequence[ProfileAnswerInput],
    step: ProfileWizardStep | None,
    phone_number_parser: PhoneNumberParserContract,
    country_code: CountryCode,
) -> list[ProfileAnswer]:
    """
    Replace the answers of one step (or of all steps when `step` is None).

    Answers of other steps are kept; answers to questions the niche does not
    have (after a niche change) are dropped. Result follows question order.

    Raises:
        ValidationFailedError: unknown question, question of another step,
            duplicate question, or an answer of the wrong shape.
    """

    questions_by_key: dict[QuestionKey, QuestionDefinition] = {
        question.key: question for question in template.questions
    }
    new_answers: dict[QuestionKey, ProfileAnswer | None] = {}
    for answer_input in answer_inputs:
        question: QuestionDefinition | None = questions_by_key.get(
            answer_input.question_key
        )
        if question is None:
            raise ValidationFailedError(
                f"Question {answer_input.question_key} does not exist in niche "
                f"{template.key}."
            )

        if step is not None and question.step is not step:
            raise ValidationFailedError(
                f"Question {question.key} belongs to step {question.step}, not "
                f"to step {step}."
            )

        if question.key in new_answers:
            raise ValidationFailedError(f"Question {question.key} is answered twice.")

        new_answers[question.key] = normalize_answer(
            question=question,
            answer_input=answer_input,
            phone_number_parser=phone_number_parser,
            country_code=country_code,
        )

    current_by_key: dict[QuestionKey, ProfileAnswer] = {
        answer.question_key: answer for answer in current_answers
    }
    merged: list[ProfileAnswer] = []
    for question in template.questions:
        is_replaced: bool = step is None or question.step is step
        answer: ProfileAnswer | None = (
            new_answers.get(question.key)
            if is_replaced
            else current_by_key.get(question.key)
        )
        if answer is not None:
            merged.append(answer)

    return merged


def normalize_answer(
    question: QuestionDefinition,
    answer_input: ProfileAnswerInput,
    phone_number_parser: PhoneNumberParserContract,
    country_code: CountryCode,
) -> ProfileAnswer | None:
    """Canonical answer for one question, or None when the answer is empty."""

    text: str = "" if answer_input.answer is None else answer_input.answer.strip()
    choice_keys: list[QuestionChoiceKey] = answer_input.choice_keys
    if text == "" and choice_keys == []:
        return None

    canonical: str
    match question.answer_type:
        case QuestionAnswerType.SHORT_TEXT | QuestionAnswerType.LONG_TEXT:
            canonical = normalize_free_text(question, text, choice_keys)
        case QuestionAnswerType.NUMBER:
            canonical = normalize_number(question, text, choice_keys)
        case QuestionAnswerType.YES_NO:
            canonical = normalize_yes_no(question, text, choice_keys)
        case QuestionAnswerType.SINGLE_CHOICE | QuestionAnswerType.MULTIPLE_CHOICE:
            canonical = normalize_choices(question, text, choice_keys)
        case QuestionAnswerType.URL:
            canonical = normalize_url(question, text, choice_keys)
        case QuestionAnswerType.PHONE_NUMBER:
            reject_choices(question, choice_keys)
            details: PhoneNumberDetails = phone_number_parser.parse(
                RawPhoneNumberInput(text),
                country_hint=country_code,
            )
            canonical = details.e164

    return ProfileAnswer(question_key=question.key, answer=ProfileAnswerText(canonical))


def normalize_free_text(
    question: QuestionDefinition,
    text: str,
    choice_keys: list[QuestionChoiceKey],
) -> str:
    reject_choices(question, choice_keys)
    max_length: int = (
        MAX_SHORT_TEXT_LENGTH
        if question.answer_type is QuestionAnswerType.SHORT_TEXT
        else MAX_LONG_TEXT_LENGTH
    )
    if len(text) > max_length:
        raise ValidationFailedError(
            f"Answer to {question.key} is longer than {max_length} characters."
        )

    return text


def normalize_number(
    question: QuestionDefinition,
    text: str,
    choice_keys: list[QuestionChoiceKey],
) -> str:
    reject_choices(question, choice_keys)
    if not text.isdecimal():
        raise ValidationFailedError(
            f"Answer to {question.key} must be a whole non-negative number."
        )

    return str(int(text))


def normalize_yes_no(
    question: QuestionDefinition,
    text: str,
    choice_keys: list[QuestionChoiceKey],
) -> str:
    values: list[str] = [text.casefold()] if text != "" else []
    values.extend(choice_key for choice_key in choice_keys)
    if len(values) != 1 or values[0] not in (YES_KEY, NO_KEY):
        raise ValidationFailedError(
            f"Answer to {question.key} must be exactly one of 'yes' or 'no'."
        )

    return values[0]


def normalize_choices(
    question: QuestionDefinition,
    text: str,
    choice_keys: list[QuestionChoiceKey],
) -> str:
    if text != "":
        raise ValidationFailedError(
            f"Question {question.key} is answered with choice_keys, not text."
        )

    allowed_keys: list[QuestionChoiceKey] = [choice.key for choice in question.choices]
    for choice_key in choice_keys:
        if choice_key not in allowed_keys:
            raise ValidationFailedError(
                f"{choice_key} is not a choice of question {question.key}."
            )

    if len(set(choice_keys)) != len(choice_keys):
        raise ValidationFailedError(f"Question {question.key} repeats a choice.")

    if question.answer_type is QuestionAnswerType.SINGLE_CHOICE and (
        len(choice_keys) != 1
    ):
        raise ValidationFailedError(
            f"Question {question.key} takes exactly one choice."
        )

    ordered_keys: list[QuestionChoiceKey] = [
        allowed_key for allowed_key in allowed_keys if allowed_key in choice_keys
    ]
    return CHOICE_SEPARATOR.join(ordered_keys)


def normalize_url(
    question: QuestionDefinition,
    text: str,
    choice_keys: list[QuestionChoiceKey],
) -> str:
    reject_choices(question, choice_keys)
    try:
        return WebLink(text)
    except ValueError as error:
        raise ValidationFailedError(
            f"Answer to {question.key} must be an absolute http(s) link."
        ) from error


def reject_choices(
    question: QuestionDefinition,
    choice_keys: list[QuestionChoiceKey],
) -> None:
    if choice_keys != []:
        raise ValidationFailedError(
            f"Question {question.key} is answered with text, not choice_keys."
        )


def split_choice_answer(answer: ProfileAnswerText) -> list[QuestionChoiceKey]:
    """Choice keys stored in a choice answer ("vegan,halal" -> two keys)."""

    return [
        QuestionChoiceKey(choice_key)
        for choice_key in answer.split(CHOICE_SEPARATOR)
        if choice_key != ""
    ]
