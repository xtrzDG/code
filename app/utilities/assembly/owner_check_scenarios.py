"""
The owner's own checks as autotest scenarios: each active check is one
conversation in its language that opens with its question word for word.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestExpectation, AutotestScenarioKind
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.dto.assistants.autotest_runs import (
    AutotestLanguage,
    AutotestScenario,
    OwnerCheckSpec,
)
from app.schemas.typings.assistants.constrained_strings import AutotestScenarioKey
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.schemas.typings.assistants.strings import AutotestScenarioGoal
from app.schemas.typings.localization.strings import LanguageDisplayName
from app.utilities.assembly.autotest_scenarios import KEY_SEPARATOR

GOAL_ENDINGS: dict[AutotestExpectation, str] = {
    AutotestExpectation.MUST_MENTION: "Read the answer and end the conversation.",
    AutotestExpectation.MUST_NOT_MENTION: "Read the answer and end the conversation.",
    AutotestExpectation.MUST_HAND_OFF: (
        "If the assistant offers to pass you to a person, accept."
    ),
    AutotestExpectation.MUST_CREATE_LEAD: (
        "If the assistant takes your request, give your name and phone number "
        "when asked, then end the conversation."
    ),
}


def owner_check_key(case_id: AutotestCaseId) -> AutotestScenarioKey:
    """ "owner_check__autotest_case_…": stable across the runs of a check."""

    return AutotestScenarioKey(
        KEY_SEPARATOR.join([AutotestScenarioKind.OWNER_CHECK.value, str(case_id)])
    )


def plan_owner_check_scenarios(
    cases: Sequence[AutotestCaseDocument],
    languages: Sequence[AutotestLanguage],
) -> list[AutotestScenario]:
    """
    One scenario per active check, in the order they were written; the
    language name and script come from `languages` (a tag without one is
    named by itself and gets no script check).
    """

    by_tag: dict[str, AutotestLanguage] = {
        str(language.tag): language for language in languages
    }
    scenarios: list[AutotestScenario] = []
    for case in cases:
        if not case.is_active:
            continue

        language: AutotestLanguage | None = by_tag.get(str(case.language))
        scenarios.append(
            AutotestScenario(
                key=owner_check_key(case.id),
                kind=AutotestScenarioKind.OWNER_CHECK,
                language=case.language,
                language_name=(
                    language.name
                    if language is not None
                    else LanguageDisplayName(str(case.language))
                ),
                language_script=language.script if language is not None else None,
                goal=AutotestScenarioGoal(
                    f'Ask exactly: "{case.question}". ' + GOAL_ENDINGS[case.expectation]
                ),
                owner_check=OwnerCheckSpec(
                    case_id=case.id,
                    question=case.question,
                    expectation=case.expectation,
                    expected_text=case.expected_text,
                ),
            )
        )

    return scenarios
