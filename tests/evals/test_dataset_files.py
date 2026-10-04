"""
The committed datasets cover every niche in ka/ru/en and four in he/ar,
plus the language scenarios of the restaurant (a German guest, Georgian and
Russian typed in Latin letters).
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
LANGUAGE_SCENARIO_KINDS: set[AutotestScenarioKind] = {
    AutotestScenarioKind.FOREIGN_LANGUAGE,
    AutotestScenarioKind.TRANSLITERATED,
}


def load_all() -> list[EvalDataset]:
    return [load_dataset(path) for path in list_dataset_paths(DATASETS)]


def test_every_niche_has_a_dataset() -> None:
    assert {dataset.niche for dataset in load_all()} == set(NicheKey)


@pytest.mark.parametrize("dataset", load_all(), ids=lambda dataset: dataset.niche.value)
def test_eight_scenarios_per_language(dataset: EvalDataset) -> None:
    counts = Counter(
        scenario.language
        for scenario in dataset.scenarios
        if scenario.kind not in LANGUAGE_SCENARIO_KINDS
    )
    expected: set[str] = set(BASE_LANGUAGES)
    if dataset.niche.value in RTL_NICHES:
        expected |= RTL_LANGUAGES

    assert set(counts) == expected
    assert set(counts.values()) == {SCENARIOS_PER_LANGUAGE}


def test_the_restaurant_plays_the_language_scenarios() -> None:
    restaurant = next(
        dataset for dataset in load_all() if dataset.niche is NicheKey.RESTAURANT
    )

    assert sorted(
        (scenario.kind.value, scenario.language)
        for scenario in restaurant.scenarios
        if scenario.kind in LANGUAGE_SCENARIO_KINDS
    ) == [
        ("foreign_language", "de"),
        ("transliterated", "ka"),
        ("transliterated", "ru"),
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
            or expect.handoff is not None
        ), scenario.id
        assert scenario.customer and scenario.assistant, scenario.id
