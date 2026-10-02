"""Judge scores, scenario outcomes and run results for the evaluation tests."""

from app.schemas.constants.assistants import (
    AutotestOutcome,
    AutotestScenarioKind,
    JudgeCriterion,
)
from app.schemas.domain.assistants import AutotestScenarioResult, JudgeCriterionScore
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.typings.assistants.constrained_integers import (
    JudgeScore,
)
from app.schemas.typings.assistants.constrained_strings import (
    AutotestScenarioKey,
)
from app.schemas.typings.assistants.strings import (
    AutotestScenarioGoal,
)
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)
from app.schemas.typings.localization.strings import LanguageDisplayName

PERFECT: dict[str, int] = {criterion.value: 5 for criterion in JudgeCriterion}


def scores(**overrides: int) -> list[JudgeCriterionScore]:
    values: dict[str, int] = {**PERFECT, **overrides}
    return [
        JudgeCriterionScore(criterion=criterion, score=JudgeScore(values[criterion]))
        for criterion in JudgeCriterion
    ]


def scenario(
    kind: AutotestScenarioKind,
    language: str = "ka",
    script: str | None = "Geor",
    name: str = "Georgian",
) -> AutotestScenario:
    return AutotestScenario(
        key=AutotestScenarioKey(f"{kind.value}__{language}"),
        kind=kind,
        language=LanguageTag(language),
        language_name=LanguageDisplayName(name),
        language_script=ScriptCode(script) if script is not None else None,
        goal=AutotestScenarioGoal("Do something."),
    )


def result(
    kind: AutotestScenarioKind,
    outcome: AutotestOutcome,
    judge_scores: list[JudgeCriterionScore] | None = None,
) -> AutotestScenarioResult:
    return AutotestScenarioResult(
        scenario_key=AutotestScenarioKey(f"{kind.value}__en"),
        kind=kind,
        language=LanguageTag("en"),
        outcome=outcome,
        scores=judge_scores if judge_scores is not None else scores(),
    )
