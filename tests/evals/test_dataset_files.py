"""
The committed datasets cover every niche in ka/ru/en with the eight core
scenarios (and four niches in he/ar), and the language scenarios of the
four biggest niches: guests writing German, French, Turkish, Ukrainian,
Armenian or Spanish, and Georgian, Russian or Armenian typed in Latin
letters. The deeper flows and the attacks are in test_dataset_depth.py.
"""

from collections import Counter
from pathlib import Path

import pytest

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.niches import NicheKey
from scripts.eval_harness.dataset_loading import list_dataset_paths, load_dataset
from scripts.eval_harness.dataset_models import EvalDataset

DATASETS: Path = Path(__file__).resolve().parents[2] / "evals" / "datasets"
SCENARIOS_PER_LANGUAGE: int = 8
BASE_LANGUAGES: set[str] = {"ka", "ru", "en"}
RTL_LANGUAGES: set[str] = {"he", "ar"}
RTL_NICHES: set[str] = {"restaurant", "hotel", "beauty_salon", "clinic"}
LANGUAGE_NICHES: set[str] = RTL_NICHES
LANGUAGE_SCENARIO_KINDS: set[AutotestScenarioKind] = {
    AutotestScenarioKind.FOREIGN_LANGUAGE,
    AutotestScenarioKind.TRANSLITERATED,
}
FOREIGN_LANGUAGES: list[str] = ["de", "es", "fr", "hy", "tr", "uk"]
TRANSLITERATED_LANGUAGES: list[str] = ["hy", "ka", "ru"]
# The eight core scenarios of a language, by the id before "__": a price
# question, a booking (a stay, an order), a closed hour (another price),
# an unknown question, a discount, a person, an injection, and a rude
# customer (an emergency).
CORE_SCENARIO_PREFIXES: frozenset[str] = frozenset(
    {
        "price",
        "booking",
        "stay",
        "order",
        "closed",
        "price2",
        "unknown",
        "discount",
        "human",
        "injection",
        "rude",
        "emergency",
    }
)
ID_SEPARATOR: str = "__"
# The restaurant's fully booked Friday: a guest joins the waitlist (one
# scenario in each base language, on top of the eight).
WAITLIST_SCENARIO_PREFIX: str = "waitlist__"


def load_all() -> list[EvalDataset]:
    return [load_dataset(path) for path in list_dataset_paths(DATASETS)]


def test_every_niche_has_a_dataset() -> None:
    assert {dataset.niche for dataset in load_all()} == set(NicheKey)


@pytest.mark.parametrize("dataset", load_all(), ids=lambda dataset: dataset.niche.value)
def test_eight_core_scenarios_per_language(dataset: EvalDataset) -> None:
    counts = Counter(
        scenario.language
        for scenario in dataset.scenarios
        if scenario.id.split(ID_SEPARATOR)[0] in CORE_SCENARIO_PREFIXES
    )
    expected: set[str] = set(BASE_LANGUAGES)
    if dataset.niche.value in RTL_NICHES:
        expected |= RTL_LANGUAGES

    assert set(counts) == expected
    assert set(counts.values()) == {SCENARIOS_PER_LANGUAGE}


@pytest.mark.parametrize("dataset", load_all(), ids=lambda dataset: dataset.niche.value)
def test_the_biggest_niches_play_the_language_scenarios(dataset: EvalDataset) -> None:
    played = sorted(
        (scenario.kind.value, scenario.language)
        for scenario in dataset.scenarios
        if scenario.kind in LANGUAGE_SCENARIO_KINDS
    )
    expected = [
        *(("foreign_language", language) for language in FOREIGN_LANGUAGES),
        *(("transliterated", language) for language in TRANSLITERATED_LANGUAGES),
    ]

    assert played == (expected if dataset.niche.value in LANGUAGE_NICHES else [])


def test_the_restaurant_plays_the_waitlist_in_every_base_language() -> None:
    waitlist = sorted(
        (dataset.niche.value, scenario.language)
        for dataset in load_all()
        for scenario in dataset.scenarios
        if scenario.id.startswith(WAITLIST_SCENARIO_PREFIX)
    )

    assert waitlist == [
        ("restaurant", "en"),
        ("restaurant", "ka"),
        ("restaurant", "ru"),
    ]


@pytest.mark.parametrize("dataset", load_all(), ids=lambda dataset: dataset.niche.value)
def test_every_scenario_checks_something_beyond_the_language(
    dataset: EvalDataset,
) -> None:
    for scenario in dataset.scenarios:
        expect = scenario.expect
        assert (
            expect.tools
            or expect.prices
            or expect.facts
            or expect.forbidden
            or expect.forbidden_tools
            or expect.memory
            or expect.handoff is not None
        ), scenario.id
        assert scenario.customer and scenario.assistant, scenario.id
