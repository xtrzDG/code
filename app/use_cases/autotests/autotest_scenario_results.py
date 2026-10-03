"""The result of one autotest scenario and what the assistant's replies cost."""

from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.schemas.constants.assistants import AutotestOutcome
from app.schemas.domain.assistants import (
    AutotestScenarioResult,
    AutotestTranscriptLine,
)
from app.schemas.dto.assistants.autotest_runs import (
    AutotestCheckFailure,
    AutotestScenarioRun,
    JudgeVerdict,
)
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.prefixed_id import ConversationId


def sum_assistant_costs(
    message_repo: MessageRepoContract,
    scenario_run: AutotestScenarioRun,
    replies: list[AssistantReply],
) -> CostMicroUsd:
    """What the assistant's replies of the scenario cost, per conversation."""

    conversation_ids: dict[str, ConversationId] = {}
    for reply in replies:
        conversation_ids.setdefault(str(reply.conversation_id), reply.conversation_id)

    return CostMicroUsd(
        sum(
            int(message.cost_micro_usd)
            for conversation_id in conversation_ids.values()
            for message in message_repo.list_by_conversation(
                scenario_run.business.id,
                conversation_id,
            )
        )
    )


def build_scenario_result(
    scenario_run: AutotestScenarioRun,
    outcome: AutotestOutcome,
    *,
    transcript: list[AutotestTranscriptLine],
    check_failures: list[AutotestCheckFailure],
    cost: CostMicroUsd,
    verdict: JudgeVerdict | None = None,
) -> AutotestScenarioResult:
    return AutotestScenarioResult(
        scenario_key=scenario_run.scenario.key,
        kind=scenario_run.scenario.kind,
        language=scenario_run.scenario.language,
        outcome=outcome,
        scores=list(verdict.scores) if verdict is not None else [],
        judge_notes=list(verdict.notes) if verdict is not None else [],
        check_notes=[failure.note for failure in check_failures],
        check_codes=[failure.code for failure in check_failures],
        transcript=list(transcript),
        cost_micro_usd=cost,
    )
