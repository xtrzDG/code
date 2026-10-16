"""
A scenario that cannot be played as written fails when its dataset loads:
a language that does not fit its kind, an evaluation flow without a goal,
a customer setup in the owner's test chat, a photo that is not there, and
a memory fact the scenario never seeded.
"""

from pathlib import Path

import pytest

from app.schemas.typings.localization.constrained_strings import CurrencyCode
from scripts.eval_harness.dataset_loading import build_expectations
from scripts.eval_harness.dataset_models import ScenarioSpec
from scripts.eval_harness.dataset_validation import (
    ScenarioError,
    check_scenario,
    describe_memory,
    media_directory,
)

LANGUAGES: list[str] = ["ka", "ru", "en"]
BOOKING: dict[str, object] = {"date": "2026-10-08", "time": "19:00", "party_size": 2}
EARLIER: dict[str, object] = {
    "summary": "Asked how much the Adjarian khachapuri costs.",
    "note": "Regular guest, prefers the corner table.",
}


def spec(**fields: object) -> ScenarioSpec:
    values: dict[str, object] = {
        "id": "a",
        "language": "en",
        "kind": "price_question",
        "persona": {"name": "Emma", "phone": "+447911123456"},
        "customer": ["How much is it?"],
        "assistant": [{"say": "It costs 22 GEL."}],
    }
    values.update(fields)
    return ScenarioSpec.model_validate(values)


def customer(**fields: object) -> ScenarioSpec:
    return spec(channel="whatsapp", **fields)


def check(scenario: ScenarioSpec, media: Path = Path("/nonexistent")) -> None:
    check_scenario(scenario, LANGUAGES, media)


@pytest.mark.parametrize(
    ("scenario", "message"),
    [
        (spec(kind="foreign_language", language="ru"), "only a foreign-language"),
        (spec(language="de"), "only a foreign-language"),
        (spec(kind="reschedule"), "needs a goal"),
        (spec(setup={"booking": BOOKING}), "played on whatsapp"),
        (
            customer(persona={"name": "Emma"}, attachment={"voice_note": True}),
            "played on whatsapp",
        ),
        (customer(attachment={}), "either a voice note or a photo"),
        (
            customer(attachment={"voice_note": True, "photo": "a.png"}),
            "either a voice note or a photo",
        ),
        (customer(attachment={"photo": "missing.png"}), "no photo"),
        (
            spec(assistant=[{"sees_photo": True, "say": "That is a khachapuri."}]),
            "sees a photo nobody sent",
        ),
        (
            customer(setup={"earlier": EARLIER}, expect={"memory": ["lobiani"]}),
            "not in what the scenario seeded",
        ),
        (spec(expect={"memory": ["khachapuri"]}), "not in what the scenario seeded"),
    ],
)
def test_an_unplayable_scenario_is_refused(
    scenario: ScenarioSpec, message: str
) -> None:
    with pytest.raises(ScenarioError, match=message):
        check(scenario)


def test_playable_scenarios_pass(tmp_path: Path) -> None:
    (tmp_path / "menu.png").write_bytes(b"png")

    check(spec(kind="foreign_language", language="de"))
    check(spec(kind="transliterated", language="hy"))
    check(spec(kind="my_bookings", goal="Ask when your table is."))
    check(
        customer(
            setup={"booking": BOOKING, "earlier": EARLIER},
            expect={"memory": [["lobiani", "KHACHAPURI"], "19:00"]},
        )
    )
    check(
        customer(
            attachment={"photo": "menu.png"},
            assistant=[{"sees_photo": True, "say": "It costs 22 GEL."}],
        ),
        tmp_path,
    )
    check_scenario(spec(language="de"), [], tmp_path)


def test_photos_live_next_to_the_datasets() -> None:
    assert media_directory(Path("evals/datasets/hotel.yaml")) == Path("evals/media")


def test_the_seeded_memory_is_the_summaries_orders_and_bookings() -> None:
    described = describe_memory(
        customer(
            setup={
                "booking": BOOKING,
                "earlier": {**EARLIER, "lead": "5 x bulk pack"},
            }
        ).setup
    )

    assert described.split("\n") == [
        str(EARLIER["summary"]),
        "5 x bulk pack",
        "2026-10-08",
        "19:00",
    ]
    assert describe_memory(None) == ""


def test_the_expectations_carry_memory_and_private_values() -> None:
    expectations = build_expectations(
        customer(
            kind="returning_customer",
            goal="Come back.",
            setup={
                "earlier": EARLIER,
                "other_customer": {"name": "Giorgi Beridze", "phone": "+995599112233"},
            },
            expect={"memory": [["Adjarian khachapuri", "khachapuri"]], "no_leak": True},
        ),
        CurrencyCode("GEL"),
    )

    assert [
        [str(value) for value in group.values]
        for group in expectations.remembered_facts
    ] == [["Adjarian khachapuri", "khachapuri"]]
    assert expectations.is_leak_checked
    assert [str(value) for value in expectations.private_values] == [
        str(EARLIER["note"]),
        "Giorgi Beridze",
        "+995599112233",
    ]
    assert build_expectations(spec(), CurrencyCode("GEL")).private_values == []
