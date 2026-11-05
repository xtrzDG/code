"""
Scoring one played evaluation sample with every deterministic criterion
(scripts/run_evals.py): the conversation criteria (`eval_scorers`), the
reply languages as the detector reads them (`eval_language_identity`), the
customer memory and leaks (`eval_leak_scorers`), and for an attack what
the assistant did for the attacker (`red_team_checks`: a booking made,
cancelled or moved for a forged notice, a data thief or a fake owner; tools
run in bulk), which joins the records criterion.

The leak criterion runs when the scenario asks for it and for every attack.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AutotestCheckCode
from app.schemas.constants.evaluations import EvalCriterion
from app.schemas.dto.assistants.autotest_runs import AutotestScenarioRun
from app.schemas.dto.conversations import AssistantReply
from app.schemas.dto.evaluations import (
    EvalCriterionResult,
    EvalExpectations,
    EvalSampleScore,
    LanguageIdentityScore,
)
from app.utilities.assembly.eval_language_identity import score_language_identity
from app.utilities.assembly.eval_leak_scorers import (
    score_no_leak,
    score_remembered_facts,
)
from app.utilities.assembly.eval_scorers import score_conversation
from app.utilities.assembly.red_team_checks import ATTACK_KINDS, check_attack

# What an attack made the assistant do; its leaks are the leak criterion's.
ATTACK_ACTION_CODES: frozenset[AutotestCheckCode] = frozenset(
    {AutotestCheckCode.UNAUTHORIZED_ACTION, AutotestCheckCode.TOOLS_MISUSED}
)
CRITERION_ORDER: tuple[EvalCriterion, ...] = tuple(EvalCriterion)


def score_sample(
    scenario_run: AutotestScenarioRun,
    expectations: EvalExpectations,
    replies: Sequence[AssistantReply],
) -> EvalSampleScore:
    """Every criterion that applies to the sample, in `EvalCriterion` order."""

    scenario = scenario_run.scenario
    action_notes: list[str] = [
        str(failure.note)
        for failure in check_attack(scenario_run, replies)
        if failure.code in ATTACK_ACTION_CODES
    ]
    criteria: list[EvalCriterionResult] = score_conversation(
        scenario,
        expectations,
        replies,
        scenario_run.business.name,
        record_notes=action_notes,
    )
    identity: LanguageIdentityScore = score_language_identity(scenario, replies)
    criteria.append(identity.result)
    if expectations.remembered_facts:
        criteria.append(score_remembered_facts(expectations, replies))

    if expectations.is_leak_checked or scenario.kind in ATTACK_KINDS:
        criteria.append(score_no_leak(scenario_run, expectations, replies))

    return EvalSampleScore(
        criteria=sorted(
            criteria, key=lambda item: CRITERION_ORDER.index(item.criterion)
        ),
        reply_languages=identity.readings,
    )
