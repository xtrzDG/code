"""
Every vertical's evaluation set is at least 100 scenarios deep (AI-08):
the core flows and attacks, a grounding set of question-answer pairs in
English and Italian (questions the business's data answers and questions
it does not, which must be recorded rather than guessed), and four voice
notes the speech recognition got partly wrong (AI-12): a homophone, lost
words, an Italian accent and a misheard number, on which nothing is booked
or ordered before the customer confirms.
"""

from collections import Counter
from pathlib import Path

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.evaluations import EvalFlowKind
from scripts.eval_harness.dataset_models import EvalDataset, ScenarioSpec
from scripts.eval_harness.dataset_setup_models import ScenarioChannel
from scripts.eval_harness.dataset_validation import ScenarioError, check_scenario
from scripts.eval_harness.grounding_check import is_unanswerable
from scripts.eval_harness.question_pairs import QUESTION_ID_PREFIX
from tests.evals.test_dataset_files import load_all

MIN_SCENARIOS_PER_VERTICAL: int = 100
GROUNDING_LANGUAGES: tuple[str, ...] = ("en", "it")
# Niches whose core scenarios already reach the floor play no extra pairs.
NICHES_WITHOUT_PAIRS: frozenset[str] = frozenset({"restaurant"})
MIN_UNKNOWN_PER_LANGUAGE: int = 2
ASR_SCENARIOS: tuple[str, ...] = (
    "asr_homophone__en",
    "asr_dropped__it",
    "asr_accent__en",
    "asr_number__it",
)
ACTING_TOOLS: frozenset[AssistantToolName] = frozenset(
    {AssistantToolName.CREATE_BOOKING, AssistantToolName.CREATE_LEAD}
)
DATASETS: list[EvalDataset] = load_all()


def pairs(dataset: EvalDataset) -> list[ScenarioSpec]:
    return [s for s in dataset.scenarios if s.id.startswith(QUESTION_ID_PREFIX)]


@pytest.mark.parametrize("dataset", DATASETS, ids=lambda dataset: dataset.niche.value)
def test_every_vertical_plays_at_least_a_hundred_scenarios(
    dataset: EvalDataset,
) -> None:
    assert len(dataset.scenarios) >= MIN_SCENARIOS_PER_VERTICAL


@pytest.mark.parametrize("dataset", DATASETS, ids=lambda dataset: dataset.niche.value)
def test_the_grounding_set_asks_in_english_and_italian(dataset: EvalDataset) -> None:
    grounding = pairs(dataset)
    if dataset.niche.value in NICHES_WITHOUT_PAIRS:
        assert grounding == []
        return

    unknown = Counter(s.language for s in grounding if is_unanswerable(s))
    answered = Counter(s.language for s in grounding if not is_unanswerable(s))

    assert {s.language for s in grounding} == set(GROUNDING_LANGUAGES)
    assert "it" in dataset.business.languages
    for language in GROUNDING_LANGUAGES:
        assert unknown[language] >= MIN_UNKNOWN_PER_LANGUAGE, language
        assert answered[language] > unknown[language], language


@pytest.mark.parametrize("dataset", DATASETS, ids=lambda dataset: dataset.niche.value)
def test_no_question_is_a_copy_of_another(dataset: EvalDataset) -> None:
    asked = Counter(s.customer[0].casefold() for s in pairs(dataset))

    assert [question for question, count in asked.items() if count > 1] == []


@pytest.mark.parametrize("dataset", DATASETS, ids=lambda dataset: dataset.niche.value)
def test_an_unknown_pair_records_the_question_and_names_its_guesses(
    dataset: EvalDataset,
) -> None:
    for scenario in pairs(dataset):
        if not is_unanswerable(scenario):
            continue

        assert scenario.expect.tools == [
            AssistantToolName.RECORD_UNANSWERED_QUESTION
        ], scenario.id
        assert scenario.expect.invented, scenario.id


@pytest.mark.parametrize("dataset", DATASETS, ids=lambda dataset: dataset.niche.value)
def test_every_vertical_plays_four_misrecognised_voice_notes(
    dataset: EvalDataset,
) -> None:
    noisy = {s.id: s for s in dataset.scenarios if s.kind is EvalFlowKind.ASR_NOISE}

    assert sorted(noisy) == sorted(ASR_SCENARIOS)
    for scenario in noisy.values():
        assert scenario.channel is ScenarioChannel.WHATSAPP, scenario.id
        assert scenario.attachment is not None and scenario.attachment.voice_note
        assert scenario.expect.handoff is False, scenario.id


@pytest.mark.parametrize("dataset", DATASETS, ids=lambda dataset: dataset.niche.value)
def test_a_misheard_number_is_asked_back_before_anything_is_booked(
    dataset: EvalDataset,
) -> None:
    misheard = next(s for s in dataset.scenarios if s.id == "asr_number__it")

    assert ACTING_TOOLS & set(misheard.expect.forbidden_tools)
    assert misheard.expect.facts, "the reply repeats what it understood"
    assert all(step.call is None for step in misheard.assistant)


def test_a_misrecognised_voice_note_must_be_a_voice_note() -> None:
    scenario = ScenarioSpec.model_validate(
        {
            "id": "asr_number__it",
            "language": "it",
            "kind": "asr_noise",
            "channel": "whatsapp",
            "persona": {"name": "Giulia", "phone": "+393471234567"},
            "goal": "Book on Thursday at six.",
            "customer": ["vorrei prenotare giovedì alle 6"],
            "assistant": [{"say": "Intende alle 18:00?"}],
        }
    )

    with pytest.raises(ScenarioError, match="voice note"):
        check_scenario(scenario, ["en", "it"], Path("/nonexistent"))
