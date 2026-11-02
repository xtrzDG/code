"""
The owner's texts that join the assistant's instruction (the tone, the
cases to hand off, the prohibitions) are checked as instructions before
they are stored, on every save path (a wizard step, the whole profile, the
setup autosave): each must be an `OwnerRuleInstruction` or an
`OwnerToneInstruction`, on one line and without the characters of the
platform's headers and fences. The instruction fences them as the owner's
text as well (`owner_text_fencing`), also those stored before this check.
"""

from collections.abc import Sequence

from base_typed_string import BaseTypedStringConstraintViolationError

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.profiles.constrained_strings import (
    OwnerRuleInstruction,
    OwnerToneInstruction,
)
from app.schemas.typings.profiles.strings import (
    ForbiddenRuleText,
    HandoffRuleText,
    ToneText,
)

REFUSAL_DETAIL: str = (
    "must be one line without < > [ ] { } ` characters and must not start with #."
)


def check_rule_instructions[RuleText: (HandoffRuleText, ForbiddenRuleText)](
    rules: Sequence[RuleText], subject: str
) -> list[RuleText]:
    """
    The rules as given, each readable as an `OwnerRuleInstruction`.

    Raises:
        ValidationFailedError: a rule spans lines or carries the characters
            of the instruction's headers and fences.
    """

    for rule in rules:
        try:
            OwnerRuleInstruction(str(rule).strip())
        except BaseTypedStringConstraintViolationError as error:
            raise ValidationFailedError(
                f"Each {subject} rule {REFUSAL_DETAIL}"
            ) from error

    return list(rules)


def check_tone_instruction(tone: ToneText | None) -> ToneText | None:
    """
    The tone as given, readable as an `OwnerToneInstruction`; None stays None.

    Raises:
        ValidationFailedError: the tone spans lines or carries the
            characters of the instruction's headers and fences.
    """

    if tone is None:
        return None

    try:
        OwnerToneInstruction(str(tone).strip())
    except BaseTypedStringConstraintViolationError as error:
        raise ValidationFailedError(f"The tone {REFUSAL_DETAIL}") from error

    return tone
