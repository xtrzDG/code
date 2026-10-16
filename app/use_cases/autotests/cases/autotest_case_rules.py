"""
The rules of the owner's checks: what each expectation needs, how many a
business keeps, and when two checks are the same.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestExpectation
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.assistants.constrained_integers import AutotestCaseLimit
from app.schemas.typings.assistants.constrained_strings import (
    AutotestCaseQuestion,
    AutotestExpectedText,
)
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.utilities.knowledge.search_text import fold_words

# Every check runs in every apply: a few dozen keep it quick.
AUTOTEST_CASE_LIMIT: AutotestCaseLimit = AutotestCaseLimit(50)
TEXT_EXPECTATIONS: frozenset[AutotestExpectation] = frozenset(
    {AutotestExpectation.MUST_MENTION, AutotestExpectation.MUST_NOT_MENTION}
)


def check_expected_text(
    expectation: AutotestExpectation,
    expected_text: AutotestExpectedText | None,
) -> AutotestExpectedText | None:
    """
    The expected text a check keeps: required when the answer must (not)
    mention it, dropped for a handoff or a request.

    Raises:
        ValidationFailedError: a text expectation without its text.
    """

    if expectation not in TEXT_EXPECTATIONS:
        return None

    if expected_text is None or fold_words(str(expected_text)) == "":
        raise ValidationFailedError(
            "Write the word or phrase the answer must (or must not) mention."
        )

    return AutotestExpectedText(str(expected_text).strip())


def check_room(cases: Sequence[AutotestCaseDocument]) -> None:
    """
    Raises:
        ValidationFailedError: the business keeps as many checks as it may.
    """

    if len(cases) >= int(AUTOTEST_CASE_LIMIT):
        raise ValidationFailedError(
            f"A business keeps at most {AUTOTEST_CASE_LIMIT} checks; "
            "delete one you no longer need."
        )


def check_unique(
    cases: Sequence[AutotestCaseDocument],
    question: AutotestCaseQuestion,
    expectation: AutotestExpectation,
    expected_text: AutotestExpectedText | None,
    own_id: AutotestCaseId | None = None,
) -> None:
    """
    Raises:
        ConflictError: another check asks the same question (ignoring case,
            accents and punctuation) and expects the same.
    """

    key: tuple[str, AutotestExpectation, str] = (
        fold_words(str(question)),
        expectation,
        fold_words(str(expected_text or "")),
    )
    for case in cases:
        if case.id == own_id:
            continue

        if (
            fold_words(str(case.question)),
            case.expectation,
            fold_words(str(case.expected_text or "")),
        ) == key:
            raise ConflictError("The same check already exists.")
