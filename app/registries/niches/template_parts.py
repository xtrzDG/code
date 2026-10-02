"""Building blocks shared by the sixteen niche templates.

The platform rules every niche follows (AI disclosure, facts only, prices
only from the price list, confirmation before booking, handoff on request,
resistance to "forget your instructions") are written once, in the
instruction sections (`app/utilities/assembly/instruction_sections.py`).
Every niche also gets the same base autotest scenarios and the same
forbidden basics; a template adds only what its niche changes: its own
rules and two or three short example exchanges.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.niches import (
    ExampleExchangeKind,
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
from app.utilities.knowledge.localized_texts import (
    build_localized_rule_lines,
    build_localized_text,
)

COMMON_FORBIDDEN_RULES_EN: tuple[str, ...] = (
    "Discounts or special prices without approval",
    "Promises beyond the profile",
)
COMMON_FORBIDDEN_RULES_RU: tuple[str, ...] = (
    "Скидки и особые цены без согласования",
    "Обещания сверх анкеты",
)
COMMON_FORBIDDEN_RULES_KA: tuple[str, ...] = (
    "ფასდაკლებები და განსაკუთრებული ფასები შეთანხმების გარეშე",
    "დაპირებები, რომლებიც ანკეტაში არ არის",
)

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


def text(en: str, ru: str, ka: str | None = None) -> LocalizedText:
    """Owner-facing text: English and Russian always, Georgian where available."""

    return build_localized_text(en=en, ru=ru, ka=ka)


def choice(
    key: QuestionChoiceKey,
    en: str,
    ru: str,
    ka: str | None = None,
) -> QuestionChoice:
    """One predefined answer of a choice question."""

    return QuestionChoice(key=key, labels=text(en=en, ru=ru, ka=ka))


def question(
    key: QuestionKey,
    step: ProfileWizardStep,
    answer_type: QuestionAnswerType,
    labels: LocalizedText,
    *,
    is_required: IsQuestionRequired = False,
    hints: LocalizedText | None = None,
    choices: Sequence[QuestionChoice] = (),
    fact_key: FactKey | None = None,
) -> QuestionDefinition:
    """
    A niche question; its answer becomes the fact `fact_key`.

    The fact key defaults to the question key, which is a separate,
    explicitly validated primitive. YES_NO questions get the localized
    "yes"/"no" choices so every client renders them the same way.
    """

    question_choices: list[QuestionChoice] = list(choices)
    if answer_type is QuestionAnswerType.YES_NO and question_choices == []:
        question_choices = yes_no_choices()

    return QuestionDefinition(
        key=key,
        step=step,
        answer_type=answer_type,
        is_required=is_required,
        labels=labels,
        hints=hints,
        choices=question_choices,
        fact_key=fact_key if fact_key is not None else FactKey(str(key)),
    )


def yes_no_choices() -> list[QuestionChoice]:
    """The two canonical answers of a YES_NO question ("yes" and "no")."""

    return [
        choice(QuestionChoiceKey("yes"), "Yes", "Да", "დიახ"),
        choice(QuestionChoiceKey("no"), "No", "Нет", "არა"),
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


def handoff_rules(
    en: Sequence[str],
    ru: Sequence[str],
    ka: Sequence[str],
) -> LocalizedText:
    """Default handoff rules of a niche, one rule per line."""

    return build_localized_rule_lines(en=en, ru=ru, ka=ka)


def forbidden_rules(
    en: Sequence[str],
    ru: Sequence[str],
    ka: Sequence[str],
) -> LocalizedText:
    """Platform forbidden rules followed by the niche's own, one rule per line."""

    return build_localized_rule_lines(
        en=(*COMMON_FORBIDDEN_RULES_EN, *en),
        ru=(*COMMON_FORBIDDEN_RULES_RU, *ru),
        ka=(*COMMON_FORBIDDEN_RULES_KA, *ka),
    )


def autotest_kinds(
    *extra_kinds: AutotestScenarioKind,
) -> list[AutotestScenarioKind]:
    """Base scenarios every assistant must pass, plus niche-specific ones."""

    return [*BASE_AUTOTEST_KINDS, *extra_kinds]
