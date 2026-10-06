"""Building blocks shared by the sixteen niche templates.

The platform rules every niche follows (AI disclosure, facts only, prices
only from the price list, confirmation before booking, handoff on request,
resistance to "forget your instructions") are written once, in the
instruction sections (`app/utilities/assembly/instruction_sections.py`).
Every niche also gets the same base autotest scenarios and the same
forbidden basics; a template adds only what its niche changes: its own
rules and two or three short example exchanges.

The owner-facing texts (names, questions, hints, choices, default handoff
and forbidden rules) live in the owner text catalog under
`niches.<niche>.*` (`app/registries/localization/texts/<language>.json`),
so they exist in every cabinet language. Prompt rules and example
exchanges stay here: they are English text for the model, and the
assistant prompt reads only the English catalog values.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.niches import (
    ExampleExchangeKind,
    NicheKey,
    ProfileWizardStep,
    QuestionAnswerType,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.dto.niches import (
    NicheExampleExchange,
    QuestionChoice,
    QuestionDefinition,
)
from app.schemas.typings.assistants.strings import PromptRuleText
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.schemas.typings.niches.booleans import IsQuestionRequired
from app.schemas.typings.niches.strings import (
    ExampleAssistantLine,
    ExampleCustomerLine,
)
from app.schemas.typings.profiles.constrained_strings import (
    FactKey,
    QuestionChoiceKey,
    QuestionKey,
)
from app.utilities.knowledge.localized_texts import RULE_LINE_SEPARATOR
from app.utilities.localization.owner_texts import (
    has_owner_text,
    owner_rule_lines,
    owner_text,
)

NICHE_TEXT_AREA: str = "niches"
COMMON_TEXTS: str = "niches.common"
QUESTIONS: str = "questions"
CHOICES: str = "choices"

BASE_AUTOTEST_KINDS: tuple[AutotestScenarioKind, ...] = (
    AutotestScenarioKind.BOOKING,
    AutotestScenarioKind.BOOKING_OUT_OF_HOURS,
    AutotestScenarioKind.CANCELLATION,
    AutotestScenarioKind.PRICE_QUESTION,
    AutotestScenarioKind.UNKNOWN_QUESTION,
    AutotestScenarioKind.DISCOUNT_REQUEST,
    AutotestScenarioKind.RUDE_CUSTOMER,
    AutotestScenarioKind.HUMAN_REQUEST,
    AutotestScenarioKind.PROMPT_INJECTION,
)
# Every assistant also answers languages the business did not list and its
# own languages typed in Latin letters.
LANGUAGE_AUTOTEST_KINDS: tuple[AutotestScenarioKind, ...] = (
    AutotestScenarioKind.FOREIGN_LANGUAGE,
    AutotestScenarioKind.TRANSLITERATED,
)


def niche_text_key(niche: NicheKey, *path: str) -> str:
    """The catalog key of a niche text: `niches.<niche>.<path...>`."""

    return ".".join((NICHE_TEXT_AREA, niche.value, *path))


def text(niche: NicheKey, *path: str) -> LocalizedText:
    """
    An owner-facing text of the niche from the owner text catalog
    (`niches.<niche>.<path>` in `texts/<language>.json`), in every cabinet
    language.
    """

    return owner_text(niche_text_key(niche, *path))


def choice(
    niche: NicheKey,
    question_key: QuestionKey,
    key: QuestionChoiceKey,
) -> QuestionChoice:
    """One predefined answer of a choice question."""

    return QuestionChoice(
        key=key,
        labels=text(niche, QUESTIONS, str(question_key), CHOICES, str(key)),
    )


def question(
    niche: NicheKey,
    key: QuestionKey,
    step: ProfileWizardStep,
    answer_type: QuestionAnswerType,
    *,
    is_required: IsQuestionRequired = False,
    choices: Sequence[QuestionChoiceKey] = (),
    fact_key: FactKey | None = None,
) -> QuestionDefinition:
    """
    A niche question; its answer becomes the fact `fact_key`.

    The label is the catalog text `niches.<niche>.questions.<key>.label`;
    the question has a hint when the catalog has `.hint`, and each choice
    reads `.choices.<choice>`. The fact key defaults to the question key,
    which is a separate, explicitly validated primitive. YES_NO questions
    get the localized "yes"/"no" choices so every client renders them the
    same way.
    """

    hint_key: str = niche_text_key(niche, QUESTIONS, str(key), "hint")
    question_choices: list[QuestionChoice] = [
        choice(niche, key, choice_key) for choice_key in choices
    ]
    if answer_type is QuestionAnswerType.YES_NO and question_choices == []:
        question_choices = yes_no_choices()

    return QuestionDefinition(
        key=key,
        step=step,
        answer_type=answer_type,
        is_required=is_required,
        labels=text(niche, QUESTIONS, str(key), "label"),
        hints=owner_text(hint_key) if has_owner_text(hint_key) else None,
        choices=question_choices,
        fact_key=fact_key if fact_key is not None else FactKey(str(key)),
    )


def yes_no_choices() -> list[QuestionChoice]:
    """The two canonical answers of a YES_NO question ("yes" and "no")."""

    return [
        QuestionChoice(
            key=QuestionChoiceKey(answer),
            labels=owner_text(f"{COMMON_TEXTS}.{CHOICES}.{answer}"),
        )
        for answer in ("yes", "no")
    ]


def prompt_rules(*niche_rules: str) -> list[PromptRuleText]:
    """
    The niche's own rules (English, for the model). The platform rules are
    not repeated here: the instruction sections state each of them once.
    """

    return [PromptRuleText(rule) for rule in niche_rules]


def example(
    kind: ExampleExchangeKind,
    customer_line: str,
    assistant_line: str,
) -> NicheExampleExchange:
    """
    One example exchange (English, for the model). The assistant line names
    the tool it calls in square brackets; values in angle brackets stand for
    what a tool or the facts return.
    """

    return NicheExampleExchange(
        kind=kind,
        customer_line=ExampleCustomerLine(customer_line),
        assistant_line=ExampleAssistantLine(assistant_line),
    )


def handoff_rules(niche: NicheKey) -> LocalizedText:
    """Default handoff rules of a niche, one rule per line."""

    return owner_rule_lines(niche_text_key(niche, "handoff_rules"))


def forbidden_rules(niche: NicheKey) -> LocalizedText:
    """Platform forbidden rules followed by the niche's own, one rule per line."""

    common: LocalizedText = owner_rule_lines(f"{COMMON_TEXTS}.forbidden_rules")
    own: LocalizedText = owner_rule_lines(niche_text_key(niche, "forbidden_rules"))
    return LocalizedText(
        values={
            language: LocalizedTextValue(
                f"{value}{RULE_LINE_SEPARATOR}{own.values[language]}"
            )
            for language, value in common.values.items()
            if language in own.values
        }
    )


def autotest_kinds(
    *extra_kinds: AutotestScenarioKind,
) -> list[AutotestScenarioKind]:
    """
    Base scenarios every assistant must pass, niche-specific ones, then the
    language scenarios.
    """

    return [*BASE_AUTOTEST_KINDS, *extra_kinds, *LANGUAGE_AUTOTEST_KINDS]
