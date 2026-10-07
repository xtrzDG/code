"""
An evaluation run over datasets: one container and one cassette per niche,
every selected scenario played `samples` times.
"""

from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from app.adapters.llm.llm_cassette_file_store import LlmCassetteFileStore
from app.schemas.dto.llm_cassettes import LlmCassetteRecording
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from scripts.eval_harness.business_seeding import EvalBusinessSeeder
from scripts.eval_harness.dataset_loading import list_dataset_paths, load_dataset
from scripts.eval_harness.dataset_models import EvalDataset, ScenarioSpec
from scripts.eval_harness.dataset_validation import media_directory
from scripts.eval_harness.eval_container import (
    SteppingClock,
    SwitchableLlmAdapter,
    build_environment,
    build_eval_container,
)
from scripts.eval_harness.run_results import SampleResult, ScenarioResult
from scripts.eval_harness.scenario_player import (
    EvalMode,
    NicheSession,
    RunModels,
    play_sample,
)

SCRIPTED_MODEL: LlmModelId = LlmModelId("scripted")
DEFAULT_TURN_LIMIT: int = 6

type ProgressReporter = Callable[[ScenarioResult], None]


@dataclass(frozen=True)
class RunOptions:
    datasets_dir: Path
    cassettes_dir: Path
    mode: EvalMode
    # None on replay: the models each cassette was recorded with.
    models: RunModels | None
    niches: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    scenario_ids: tuple[str, ...] = ()
    samples: int = 1
    turn_limit: int = DEFAULT_TURN_LIMIT
    workers: int = 1


@dataclass(frozen=True)
class NicheOutcome:
    niche: str
    scenarios: list[ScenarioResult]
    models: RunModels


@dataclass(frozen=True)
class RunOutcome:
    """The scenarios played and the models each niche was played with."""

    scenarios: list[ScenarioResult]
    models: dict[str, RunModels]


def run_evals(
    options: RunOptions, report_progress: ProgressReporter | None = None
) -> RunOutcome:
    """
    Every selected dataset, one niche after another, or `workers` niches at
    a time in separate processes (a live benchmark waits on providers).
    """

    paths: list[Path] = list_dataset_paths(options.datasets_dir, options.niches)
    if options.workers > 1:
        with ProcessPoolExecutor(max_workers=options.workers) as pool:
            outcomes: list[NicheOutcome | None] = list(
                pool.map(run_niche, paths, [options] * len(paths))
            )
    else:
        outcomes = [run_niche(path, options, report_progress) for path in paths]

    played: list[NicheOutcome] = [outcome for outcome in outcomes if outcome]
    return RunOutcome(
        scenarios=[scenario for outcome in played for scenario in outcome.scenarios],
        models={outcome.niche: outcome.models for outcome in played},
    )


def run_niche(
    path: Path,
    options: RunOptions,
    report_progress: ProgressReporter | None = None,
) -> NicheOutcome | None:
    """One dataset's selected scenarios; None when none is selected."""

    dataset: EvalDataset = load_dataset(path)
    selected: list[ScenarioSpec] = select_scenarios(dataset, options)
    if not selected:
        return None

    is_complete: bool = not options.languages and not options.scenario_ids
    store = LlmCassetteFileStore(
        options.cassettes_dir / f"{dataset.niche.value}.json",
        is_fresh=options.mode is EvalMode.RECORD and is_complete,
    )
    models: RunModels = choose_models(options, store.recording())
    session: NicheSession = open_session(dataset, store, options, models)
    scenarios: list[ScenarioResult] = []
    for scenario in selected:
        samples: list[SampleResult] = [
            play_sample(session, scenario, index) for index in range(options.samples)
        ]
        result = ScenarioResult(
            niche=dataset.niche.value,
            scenario_id=scenario.id,
            language=scenario.language,
            kind=scenario.kind.value,
            samples=samples,
        )
        scenarios.append(result)
        (report_progress or print_progress)(result)

    if options.mode is EvalMode.RECORD:
        store.set_recording(
            LlmCassetteRecording(
                assistant_model_id=models.assistant,
                customer_model_id=models.customer,
                judge_model_id=models.judge,
            )
        )
        store.save()

    return NicheOutcome(niche=dataset.niche.value, scenarios=scenarios, models=models)


def print_progress(scenario: ScenarioResult) -> None:
    status: str = (
        "PASS" if scenario.is_passed else "STALE" if scenario.is_stale else "FAIL"
    )
    print(f"{status:5} {scenario.key}", flush=True)


def select_scenarios(dataset: EvalDataset, options: RunOptions) -> list[ScenarioSpec]:
    return [
        scenario
        for scenario in dataset.scenarios
        if (not options.languages or scenario.language in options.languages)
        and (not options.scenario_ids or scenario.id in options.scenario_ids)
    ]


def choose_models(
    options: RunOptions, recording: LlmCassetteRecording | None
) -> RunModels:
    """The run's models; a replay uses the ones its cassette was recorded with."""

    if options.models is not None:
        return options.models

    if recording is None:
        return RunModels(assistant=SCRIPTED_MODEL, customer=SCRIPTED_MODEL)

    return RunModels(
        assistant=recording.assistant_model_id,
        customer=recording.customer_model_id,
        judge=recording.judge_model_id,
    )


def open_session(
    dataset: EvalDataset,
    store: LlmCassetteFileStore,
    options: RunOptions,
    models: RunModels,
) -> NicheSession:
    clock = SteppingClock()
    seam = SwitchableLlmAdapter()
    container = build_eval_container(build_environment(models.assistant), clock, seam)
    return NicheSession(
        dataset=dataset,
        container=container,
        seeder=EvalBusinessSeeder(container),
        seam=seam,
        clock=clock,
        store=store,
        mode=options.mode,
        models=models,
        turn_limit=options.turn_limit,
        media_dir=media_directory(options.datasets_dir / f"{dataset.niche.value}.yaml"),
    )
