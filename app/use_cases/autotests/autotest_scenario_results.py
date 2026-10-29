"""The result of one autotest scenario and the test conversation it left."""

from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.schemas.constants.assistants import AutotestOutcome
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import (
    AutotestScenarioResult,
    AutotestTranscriptLine,
)
from app.schemas.domain.autotest_cases import OwnerCheckSnapshot
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.assistants.autotest_runs import (
    AutotestCheckFailure,
    AutotestScenarioRun,
    JudgeVerdict,
    OwnerCheckSpec,
    ScenarioConversationTrace,
)
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.assistants.strings import JudgeNote
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId


def trace_test_conversation(
    message_repo: MessageRepoContract,
    scenario_run: AutotestScenarioRun,
    replies: list[AssistantReply],
) -> ScenarioConversationTrace:
    """
    What the assistant's replies of the scenario cost (per conversation, its
    stored messages), the conversation of the first reply and the first
    assistant message in it, which "Fix this answer" opens.
    """

    conversation_ids: dict[str, ConversationId] = {}
    for reply in replies:
        conversation_ids.setdefault(str(reply.conversation_id), reply.conversation_id)

    cost: int = 0
    first_answer: MessageId | None = None
    for conversation_id in conversation_ids.values():
        messages: list[MessageDocument] = message_repo.list_by_conversation(
            scenario_run.business.id, conversation_id
        )
        cost += sum(int(message.cost_micro_usd) for message in messages)
        if first_answer is None:
            first_answer = next(
                (
                    message.id
                    for message in messages
                    if message.author is MessageAuthor.ASSISTANT
                ),
                None,
            )

    return ScenarioConversationTrace(
        cost=CostMicroUsd(cost),
        conversation_id=next(iter(conversation_ids.values()), None),
        answer_message_id=first_answer,
    )


def build_scenario_result(
    scenario_run: AutotestScenarioRun,
    outcome: AutotestOutcome,
    *,
    transcript: list[AutotestTranscriptLine],
    check_failures: list[AutotestCheckFailure],
    cost: CostMicroUsd,
    verdict: JudgeVerdict | None = None,
    trace: ScenarioConversationTrace | None = None,
    judge_notes: list[JudgeNote] | None = None,
) -> AutotestScenarioResult:
    owner_check: OwnerCheckSpec | None = scenario_run.scenario.owner_check
    return AutotestScenarioResult(
        scenario_key=scenario_run.scenario.key,
        kind=scenario_run.scenario.kind,
        language=scenario_run.scenario.language,
        outcome=outcome,
        scores=list(verdict.scores) if verdict is not None else [],
        judge_notes=(
            list(verdict.notes) if verdict is not None else list(judge_notes or [])
        ),
        check_notes=[failure.note for failure in check_failures],
        check_codes=[failure.code for failure in check_failures],
        transcript=list(transcript),
        cost_micro_usd=cost,
        autotest_case_id=owner_check.case_id if owner_check is not None else None,
        owner_check=(
            None
            if owner_check is None
            else OwnerCheckSnapshot(
                question=owner_check.question,
                expectation=owner_check.expectation,
                expected_text=owner_check.expected_text,
            )
        ),
        conversation_id=None if trace is None else trace.conversation_id,
        answer_message_id=None if trace is None else trace.answer_message_id,
    )
