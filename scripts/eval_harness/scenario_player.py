"""
Playing one sample of one scenario: a fresh business, the model of the
sample (replayed from the cassette, or recorded from the scripted model
or a live provider), the conversation, the judge and the scorers.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.adapters.llm.recording_llm_adapter import RecordingLlmAdapter
from app.adapters.llm.replay_llm_adapter import ReplayLlmAdapter
from app.containers.app import AppContainer
from app.contracts.llm_cassettes import LlmCassetteStoreAdapterContract
from app.schemas.dto.assistants.autotest_runs import AutotestScenario, JudgeVerdict
from app.schemas.dto.evaluations import EvalCriterionResult, EvalExpectations
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.constrained_strings import (
    AutotestScenarioKey,
    LlmModelId,
)
from app.schemas.typings.assistants.strings import AutotestScenarioGoal
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.evaluations.constrained_integers import (
    LlmCassetteSampleIndex,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.utilities.assembly.autotest_evaluation import MIN_PASSING_CRITERION_SCORE
from app.utilities.assembly.autotest_prompts import build_customer_persona_prompt
from app.utilities.assembly.autotest_scenarios import DEFAULT_PARTY_SIZE, plan_scenarios
from app.utilities.assembly.eval_scorers import score_conversation
from app.utilities.assembly.fact_descriptions import RESOURCE_KIND_NOUNS
from app.utilities.assembly.fact_formatting import read_english_text
from app.utilities.assembly.language_profiles import (
    build_autotest_languages,
    collect_language_profiles,
)
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
from scripts.eval_harness.scripted_model import build_scripted_adapter


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
    planned: AutotestScenario = plan_eval_scenario(session, scenario)
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
            planned,
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

    criteria: list[EvalCriterionResult] = score_conversation(
        planned, expectations, conversation.replies, seeded.business.name
    )
    stale: list[str] = list(
        dict.fromkeys(
            str(miss.reason) for miss in ([] if replay is None else replay.misses)
        )
    )
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
            and all(result.is_passed for result in criteria)
            and (
                judge is None
                or all(
                    score >= MIN_PASSING_CRITERION_SCORE
                    for score in judge.scores.values()
                )
            )
        ),
        criteria=criteria,
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


def plan_eval_scenario(
    session: NicheSession, scenario: ScenarioSpec
) -> AutotestScenario:
    """
    The autotest scenario the dataset scenario stands for, planned like an
    autotest run plans it (language name and script, the kind's goal or the
    price question of `item`), under the dataset's id and goal.
    """

    registries = session.container.registries
    niche = registries.niche_template_registry().get(session.dataset.niche)
    tag = LanguageTag(scenario.language)
    planned: list[AutotestScenario] = plan_scenarios(
        languages=build_autotest_languages(
            [tag], collect_language_profiles(registries.language_registry(), [tag])
        ),
        kinds=[scenario.kind],
        priced_item_titles=[] if scenario.item is None else [scenario.item],
        price_question_limit=1,
        resource_noun=(
            read_english_text(niche.resource_nouns)
            or RESOURCE_KIND_NOUNS[niche.resource_kind]
        ),
        party_size=DEFAULT_PARTY_SIZE,
    )
    base: AutotestScenario = planned[-1]
    return base.model_copy(
        update={
            "key": AutotestScenarioKey(scenario.id),
            "goal": base.goal
            if scenario.goal is None
            else AutotestScenarioGoal(scenario.goal),
        }
    )
