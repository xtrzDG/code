"""
Playing one sample of one scenario: a fresh business and what the
scenario's customer already has with it, the model of the sample
(replayed from the cassette, or recorded from the scripted model or a
live provider), the conversation, the judge and the scorers.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from app.adapters.llm.recording_llm_adapter import RecordingLlmAdapter
from app.adapters.llm.replay_llm_adapter import ReplayLlmAdapter
from app.containers.app import AppContainer
from app.contracts.llm_cassettes import LlmCassetteStoreAdapterContract
from app.schemas.dto.assistants.autotest_runs import (
    AutotestScenario,
    AutotestScenarioRun,
    JudgeVerdict,
)
from app.schemas.dto.evaluations import EvalExpectations, EvalSampleScore
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AutotestRunId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.evaluations.constrained_integers import (
    LlmCassetteSampleIndex,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.utilities.assembly.autotest_evaluation import MIN_PASSING_CRITERION_SCORE
from app.utilities.assembly.autotest_prompts import build_customer_persona_prompt
from app.utilities.assembly.eval_sample_scoring import score_sample
from scripts.eval_harness.business_seeding import EvalBusinessSeeder, SeededBusiness
from scripts.eval_harness.call_metering import CallMeter
from scripts.eval_harness.conversation_loop import (
    Conversation,
    converse,
    judge_conversation,
)
from scripts.eval_harness.dataset_loading import build_expectations
from scripts.eval_harness.dataset_models import EvalDataset, ScenarioSpec
from scripts.eval_harness.eval_container import (
    SteppingClock,
    SwitchableLlmAdapter,
    build_provider_router,
)
from scripts.eval_harness.run_results import JudgeResult, SampleResult, TranscriptLine
from scripts.eval_harness.scenario_planning import (
    build_customer_side,
    plan_eval_scenario,
)
from scripts.eval_harness.scenario_seeding import seed_customer
from scripts.eval_harness.scripted_model import build_scripted_adapter

UNDETERMINED_LANGUAGE: str = "?"


class EvalMode(StrEnum):
    """Replay the committed cassettes, or record new ones while playing."""

    REPLAY = "replay"
    RECORD = "record"


@dataclass(frozen=True)
class RunModels:
    """The assistant's model, the AI customer's and the judge's (if any)."""

    assistant: LlmModelId
    customer: LlmModelId
    judge: LlmModelId | None = None


@dataclass(frozen=True)
class NicheSession:
    """Everything the scenarios of one dataset are played with."""

    dataset: EvalDataset
    container: AppContainer
    seeder: EvalBusinessSeeder
    seam: SwitchableLlmAdapter
    clock: SteppingClock
    store: LlmCassetteStoreAdapterContract
    mode: EvalMode
    models: RunModels
    turn_limit: int
    media_dir: Path


def play_sample(
    session: NicheSession, scenario: ScenarioSpec, sample_index: int
) -> SampleResult:
    session.clock.reset()
    meter = CallMeter()
    sample = LlmCassetteSampleIndex(sample_index)
    replay: ReplayLlmAdapter | None = None
    if session.mode is EvalMode.REPLAY:
        replay = ReplayLlmAdapter(session.store, sample, meter)
        session.seam.use(replay)
    else:
        session.seam.use(
            RecordingLlmAdapter(
                build_provider_router(
                    session.container, build_scripted_adapter(scenario)
                ),
                session.store,
                sample,
                session.container.time_provider.monotonic_clock(),
                meter,
            )
        )

    seeded: SeededBusiness = session.seeder.seed(
        session.dataset.niche, session.dataset.business
    )
    seed_customer(session.container, seeded, scenario, session.seeder.owner_id)
    planned: AutotestScenario = plan_eval_scenario(
        session.container, session.dataset, scenario
    )
    expectations: EvalExpectations = build_expectations(
        scenario, seeded.business.currency_code
    )
    conversation = Conversation()
    error: str | None = None
    verdict: JudgeVerdict | None = None
    try:
        converse(
            session.container,
            seeded,
            build_customer_side(
                session.container, seeded, scenario, planned, session.media_dir
            ),
            build_customer_persona_prompt(
                str(seeded.business.name),
                planned,
                None
                if scenario.persona.phone is None
                else E164PhoneNumber(scenario.persona.phone),
                seeded.version.facts,
                ContactName(scenario.persona.name),
            ),
            session.models.customer,
            session.turn_limit,
            meter,
            conversation,
        )
        if session.models.judge is not None and conversation.replies:
            verdict = judge_conversation(
                session.container, seeded, planned, session.models.judge, conversation
            )
            if verdict is None:
                error = "The judge's answer could not be read."
    except ApplicationError as raised:
        error = f"{type(raised).__name__}: {raised}"

    score: EvalSampleScore = score_sample(
        AutotestScenarioRun(
            run_id=AutotestRunId(),
            business=seeded.business,
            version=seeded.version,
            scenario=planned,
            customer_phone_number=None
            if scenario.persona.phone is None
            else E164PhoneNumber(scenario.persona.phone),
        ),
        expectations,
        conversation.replies,
    )
    stale: list[str] = describe_misses(
        [str(miss.reason) for miss in ([] if replay is None else replay.misses)]
    )
    if stale:
        # The engine met the miss as a provider error; the miss explains it.
        error = None

    judge: JudgeResult | None = (
        None
        if verdict is None
        else JudgeResult(
            scores={str(score.criterion): int(score.score) for score in verdict.scores},
            notes=[str(note) for note in verdict.notes],
        )
    )
    return SampleResult(
        sample_index=sample_index,
        is_passed=(
            error is None
            and not stale
            and all(result.is_passed for result in score.criteria)
            and (
                judge is None
                or all(
                    score >= MIN_PASSING_CRITERION_SCORE
                    for score in judge.scores.values()
                )
            )
        ),
        criteria=score.criteria,
        reply_languages=[
            UNDETERMINED_LANGUAGE
            if reading.detected_language is None
            else str(reading.detected_language)
            for reading in score.reply_languages
        ],
        judge=judge,
        transcript=[
            TranscriptLine(author=line.author.value, text=str(line.text))
            for line in conversation.transcript
        ],
        tool_calls=[
            f"{call.tool_name}({call.input_json})"
            + (" -> error " if call.is_error else " -> ")
            + str(call.result_json)
            for reply in conversation.replies
            for call in reply.tool_calls
        ],
        cost_micro_usd=meter.total_cost_micro_usd,
        turn_latencies_ms=list(conversation.turn_latencies_ms),
        stale_reasons=stale,
        error=error,
    )


def describe_misses(reasons: list[str]) -> list[str]:
    """
    The first miss is the cause; the calls after it miss because the
    conversation already went another way, so they are only counted.
    """

    if not reasons:
        return []

    later: int = len(reasons) - 1
    return [reasons[0]] + (
        [f"{later} later model call(s) of this sample were not recorded either."]
        if later
        else []
    )
