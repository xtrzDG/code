"""Datasets fail loudly when they are malformed and become typed expectations."""

from pathlib import Path

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from scripts.eval_harness.dataset_loading import (
    DatasetError,
    build_expectations,
    list_dataset_paths,
    load_dataset,
)
from scripts.eval_harness.dataset_models import ScenarioSpec

SCENARIO: str = """
  - id: {id}
    language: {language}
    kind: price_question
    persona: {{name: Emma, phone: "+447911123456"}}
    customer: ["How much?"]
    assistant: [{{say: "25 GEL."}}]
"""


def write(directory: Path, niche: str, body: str) -> Path:
    path = directory / f"{niche}.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def dataset_text(niche: str = "hotel", scenarios: str = "") -> str:
    return f"niche: {niche}\nbusiness: {{name: Test, languages: [en]}}\nscenarios:" + (
        scenarios or SCENARIO.format(id="a", language="en")
    )


def test_a_valid_dataset_loads(tmp_path: Path) -> None:
    path = write(tmp_path, "hotel", dataset_text())

    dataset = load_dataset(path)

    assert dataset.scenarios[0].id == "a"
    assert list_dataset_paths(tmp_path) == [path]
    assert list_dataset_paths(tmp_path, ["hotel"]) == [path]


@pytest.mark.parametrize(
    ("file_niche", "text", "message"),
    [
        ("hotel", "niche: [", "hotel.yaml"),
        ("hotel", "niche: hotel\nbusiness: {}\nscenarios: []\nextra: 1", "extra"),
        ("clinic", dataset_text("hotel"), "the file of niche hotel"),
        (
            "hotel",
            dataset_text(scenarios=SCENARIO.format(id="a", language="en") * 2),
            "appears twice",
        ),
        (
            "hotel",
            dataset_text(scenarios=SCENARIO.format(id="a", language="ka")),
            "which the business does not speak",
        ),
    ],
)
def test_malformed_datasets_are_refused(
    tmp_path: Path, file_niche: str, text: str, message: str
) -> None:
    path = write(tmp_path, file_niche, text)

    with pytest.raises(DatasetError, match=message):
        load_dataset(path)


def test_asking_for_a_niche_without_dataset_fails(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="No dataset for: spa"):
        list_dataset_paths(tmp_path, ["spa"])


def test_expectations_become_typed_dtos() -> None:
    spec = ScenarioSpec.model_validate(
        {
            "id": "booking__en",
            "language": "en",
            "kind": "booking",
            "persona": {"name": "Emma"},
            "customer": ["Book"],
            "assistant": [{"say": "Ok"}],
            "expect": {
                "tools": [
                    "check_availability",
                    {"create_booking": {"name": ["Emma", "Em"], "party_size": 2}},
                    {"create_lead": {"budget": None, "is_vip": True}},
                ],
                "forbidden_tools": ["create_lead"],
                "prices": ["25.50"],
                "facts": ["14:00", ["GEL", "lari"]],
                "forbidden": ["%"],
                "handoff": False,
            },
        }
    )

    expectations = build_expectations(spec, CurrencyCode("GEL"))

    assert [call.tool_name for call in expectations.tool_calls] == [
        AssistantToolName.CHECK_AVAILABILITY,
        AssistantToolName.CREATE_BOOKING,
        AssistantToolName.CREATE_LEAD,
    ]
    booking_fields = expectations.tool_calls[1].fields
    assert {
        str(k): [str(v) for v in values] for k, values in booking_fields.items()
    } == {
        "name": ["Emma", "Em"],
        "party_size": ["2"],
    }
    lead_fields = expectations.tool_calls[2].fields
    assert [str(v) for values in lead_fields.values() for v in values] == [
        "null",
        "true",
    ]
    assert int(expectations.prices[0].amount_minor) == 2550
    assert [
        [str(v) for v in group.values] for group in expectations.required_facts
    ] == [
        ["14:00"],
        ["GEL", "lari"],
    ]
    assert expectations.is_handoff_expected is False
    assert (
        build_expectations(
            spec.model_copy(
                update={"expect": spec.expect.model_copy(update={"handoff": None})}
            ),
            CurrencyCode("GEL"),
        ).is_handoff_expected
        is None
    )
