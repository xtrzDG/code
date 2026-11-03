"""
The question-answer pairs of a dataset (`questions:`) become scenarios when
it loads: a price question calls get_price, a catalog question
search_knowledge, an unknown question records itself and is unanswerable,
a fact question calls nothing; and a pair that cannot be played as written
fails the dataset.
"""

from pathlib import Path

import pytest

from app.schemas.constants.assistants import AssistantToolName, AutotestScenarioKind
from app.schemas.constants.evaluations import EvalFlowKind
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from scripts.eval_harness.dataset_loading import (
    DatasetError,
    build_expectations,
    load_dataset,
)
from scripts.eval_harness.dataset_models import EvalDataset, QuestionSpec
from scripts.eval_harness.question_pairs import (
    QuestionError,
    expand_questions,
    question_scenario,
)
from scripts.eval_harness.scenario_planning import autotest_kind

BUSINESS: dict[str, object] = {"name": "Test Gym", "languages": ["en", "it"]}


def question(**fields: object) -> QuestionSpec:
    values: dict[str, object] = {
        "id": "sauna",
        "language": "en",
        "ask": "Do you have a sauna?",
        "say": "I don't know yet; I have passed your question to the team.",
        "unknown": True,
        "invented": ["we have a sauna"],
    }
    values.update(fields)
    return QuestionSpec.model_validate(values)


def test_an_unknown_question_records_itself_and_cannot_be_answered() -> None:
    scenario = question_scenario(question())

    assert scenario.id == "qa_sauna__en"
    assert scenario.kind is AutotestScenarioKind.UNKNOWN_QUESTION
    assert scenario.customer == ["Do you have a sauna?"]
    assert scenario.goal == 'Ask: "Do you have a sauna?"'
    assert scenario.assistant[0].call == {
        AssistantToolName.RECORD_UNANSWERED_QUESTION: {
            "question": "Do you have a sauna?"
        }
    }
    assert scenario.expect.tools == [AssistantToolName.RECORD_UNANSWERED_QUESTION]
    assert scenario.expect.unanswerable is True
    assert scenario.expect.handoff is False
    assert AssistantToolName.CREATE_BOOKING in scenario.expect.forbidden_tools


def test_price_catalog_and_fact_questions_call_their_tool_or_none() -> None:
    price = question_scenario(
        question(
            id="visit",
            unknown=False,
            invented=[],
            ask="How much is one visit?",
            say="A single visit costs 25 GEL.",
            item="Single visit",
            prices=["25"],
        )
    )
    catalog = question_scenario(
        question(
            id="blend",
            language="it",
            unknown=False,
            invented=[],
            ask="Avete il blend No. 34?",
            say="Sì, costa 12 GEL.",
            search="Blend No. 34",
            prices=["12"],
        )
    )
    fact = question_scenario(
        question(
            id="saturday",
            unknown=False,
            invented=["24/7"],
            ask="When do you open on Saturday?",
            say="On Saturday we open at 09:00.",
            facts=["09:00"],
        )
    )

    assert price.assistant[0].call == {
        AssistantToolName.GET_PRICE: {"item_name": "Single visit"}
    }
    assert price.kind is AutotestScenarioKind.PRICE_QUESTION
    assert catalog.id == "qa_blend__it"
    assert catalog.assistant[0].call == {
        AssistantToolName.SEARCH_KNOWLEDGE: {"query": "Blend No. 34", "language": None}
    }
    assert fact.kind is EvalFlowKind.FACT_QUESTION
    assert autotest_kind(fact) is AutotestScenarioKind.PRICE_QUESTION
    assert [step.say for step in fact.assistant] == ["On Saturday we open at 09:00."]
    assert fact.expect.tools == [] and fact.expect.unanswerable is False


def test_invented_values_are_forbidden_in_every_reply() -> None:
    scenario = question_scenario(question())

    expectations = build_expectations(scenario, CurrencyCode("GEL"))

    assert [str(value) for value in expectations.forbidden_values] == [
        "we have a sauna"
    ]


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"item": "Sauna", "prices": ["10"]}, "names no item, price or fact"),
        ({"unknown": False, "invented": []}, "names a fact or a price"),
        (
            {"unknown": False, "invented": [], "item": "Sauna"},
            "names its price",
        ),
        (
            {"unknown": False, "item": "A", "search": "A", "prices": ["1"]},
            "a price question or a catalog question",
        ),
        ({"invented": ["passed your question"]}, "itself says the invented"),
    ],
)
def test_a_pair_that_cannot_be_played_as_written_is_refused(
    fields: dict[str, object], message: str
) -> None:
    with pytest.raises(QuestionError, match=message):
        question_scenario(question(**fields))


def test_a_dataset_without_pairs_is_left_as_it_is() -> None:
    dataset = EvalDataset.model_validate(
        {"niche": "fitness", "business": BUSINESS, "scenarios": []}
    )

    assert expand_questions(dataset) is dataset


def test_loading_adds_the_pairs_and_refuses_a_broken_one(tmp_path: Path) -> None:
    path = tmp_path / "fitness.yaml"
    path.write_text(
        "niche: fitness\n"
        "business: {name: Test Gym, languages: [en, it]}\n"
        "scenarios: []\n"
        "questions:\n"
        "- {id: sauna, language: en, unknown: true, ask: 'Sauna?', say: 'No idea.'}\n"
        "- {id: sauna, language: it, unknown: true, ask: 'Sauna?', say: 'Non so.'}\n",
        encoding="utf-8",
    )

    assert [s.id for s in load_dataset(path).scenarios] == [
        "qa_sauna__en",
        "qa_sauna__it",
    ]

    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "unknown: true, ask: 'Sauna?'", "ask: 'Sauna?'", 1
        ),
        encoding="utf-8",
    )
    with pytest.raises(DatasetError, match="names a fact or a price"):
        load_dataset(path)
