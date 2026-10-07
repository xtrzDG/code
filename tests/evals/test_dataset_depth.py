"""
The deeper scenarios of every niche, in ka, ru and en: a customer who
writes on WhatsApp to cancel, move or look up their booking (or, where
the business takes orders, their order), a returning customer the memory
recalls, a voice note and a photo; and the attacks of the autotests, in
English everywhere and also in Georgian and Russian in the four biggest
niches, each against another customer's private details.
"""

from pathlib import Path

import pytest

from app.schemas.constants.assistants import AssistantToolName, AutotestScenarioKind
from app.schemas.constants.evaluations import EvalFlowKind
from app.utilities.assembly.red_team_scenarios import ATTACK_OPENINGS
from scripts.eval_harness.dataset_models import EvalDataset, ScenarioKind, ScenarioSpec
from scripts.eval_harness.dataset_setup_models import ScenarioChannel
from scripts.eval_harness.dataset_validation import media_directory
from tests.evals.test_dataset_files import (
    BASE_LANGUAGES,
    DATASETS,
    LANGUAGE_NICHES,
    load_all,
)

BOOKING_CHANGE_KINDS: tuple[ScenarioKind, ...] = (
    AutotestScenarioKind.CANCELLATION,
    EvalFlowKind.RESCHEDULE,
    EvalFlowKind.MY_BOOKINGS,
)
CUSTOMER_FLOW_KINDS: tuple[ScenarioKind, ...] = (
    *BOOKING_CHANGE_KINDS,
    EvalFlowKind.RETURNING_CUSTOMER,
    EvalFlowKind.VOICE_NOTE,
    EvalFlowKind.PHOTO_MENU,
)
TRANSLATED_ATTACK_KINDS: tuple[AutotestScenarioKind, ...] = (
    AutotestScenarioKind.DATA_EXFILTRATION,
    AutotestScenarioKind.STAFF_IMPERSONATION,
    AutotestScenarioKind.TOOL_ABUSE,
)
CHANGE_TOOLS: set[AssistantToolName] = {
    AssistantToolName.CANCEL_BOOKING,
    AssistantToolName.RESCHEDULE_BOOKING,
}
ENGLISH: str = "en"


def by_kind(dataset: EvalDataset, kind: ScenarioKind) -> list[ScenarioSpec]:
    return [scenario for scenario in dataset.scenarios if scenario.kind == kind]


def takes_bookings(dataset: EvalDataset) -> bool:
    return any(
        scenario.kind is AutotestScenarioKind.BOOKING for scenario in dataset.scenarios
    )


@pytest.mark.parametrize("dataset", load_all(), ids=lambda dataset: dataset.niche.value)
def test_every_customer_flow_is_played_in_every_base_language(
    dataset: EvalDataset,
) -> None:
    for kind in CUSTOMER_FLOW_KINDS:
        scenarios = by_kind(dataset, kind)

        assert sorted(scenario.language for scenario in scenarios) == sorted(
            BASE_LANGUAGES
        ), kind
        assert all(
            scenario.channel is ScenarioChannel.WHATSAPP for scenario in scenarios
        ), kind


@pytest.mark.parametrize("dataset", load_all(), ids=lambda dataset: dataset.niche.value)
def test_a_booking_change_starts_from_what_the_customer_has(
    dataset: EvalDataset,
) -> None:
    for kind in BOOKING_CHANGE_KINDS:
        for scenario in by_kind(dataset, kind):
            setup = scenario.setup
            assert setup is not None, scenario.id
            if takes_bookings(dataset):
                assert setup.booking is not None, scenario.id
            else:
                assert setup.earlier is not None and setup.earlier.lead, scenario.id


@pytest.mark.parametrize("dataset", load_all(), ids=lambda dataset: dataset.niche.value)
def test_a_returning_customer_is_recalled_without_the_team_notes(
    dataset: EvalDataset,
) -> None:
    for scenario in by_kind(dataset, EvalFlowKind.RETURNING_CUSTOMER):
        earlier = None if scenario.setup is None else scenario.setup.earlier

        assert earlier is not None and earlier.note, scenario.id
        assert scenario.expect.memory and scenario.expect.no_leak, scenario.id


@pytest.mark.parametrize("dataset", load_all(), ids=lambda dataset: dataset.niche.value)
def test_voice_notes_and_photos_carry_their_media(dataset: EvalDataset) -> None:
    media: Path = media_directory(DATASETS / f"{dataset.niche.value}.yaml")
    for scenario in by_kind(dataset, EvalFlowKind.VOICE_NOTE):
        assert scenario.attachment is not None and scenario.attachment.voice_note

    for scenario in by_kind(dataset, EvalFlowKind.PHOTO_MENU):
        photo = None if scenario.attachment is None else scenario.attachment.photo

        assert photo is not None and (media / photo).is_file(), scenario.id
        assert any(step.sees_photo for step in scenario.assistant), scenario.id


@pytest.mark.parametrize("dataset", load_all(), ids=lambda dataset: dataset.niche.value)
def test_every_attack_is_played(dataset: EvalDataset) -> None:
    spoofs = by_kind(dataset, AutotestScenarioKind.PROMPT_INJECTION_SPOOF)
    languages: set[str] = (
        BASE_LANGUAGES if dataset.niche.value in LANGUAGE_NICHES else {ENGLISH}
    )

    assert [scenario.language for scenario in spoofs] == [ENGLISH]
    assert spoofs[0].customer[0] == ATTACK_OPENINGS[spoofs[0].kind]
    for kind in TRANSLATED_ATTACK_KINDS:
        scenarios = by_kind(dataset, kind)

        assert {scenario.language for scenario in scenarios} == languages, kind
        for scenario in scenarios:
            assert set(scenario.expect.forbidden_tools) >= CHANGE_TOOLS, scenario.id
            if scenario.language == ENGLISH:
                assert scenario.customer[0] == ATTACK_OPENINGS[kind], scenario.id


@pytest.mark.parametrize("dataset", load_all(), ids=lambda dataset: dataset.niche.value)
def test_an_attacker_finds_another_customer_to_ask_about(
    dataset: EvalDataset,
) -> None:
    for kind in TRANSLATED_ATTACK_KINDS:
        for scenario in by_kind(dataset, kind):
            other = None if scenario.setup is None else scenario.setup.other_customer

            assert other is not None, scenario.id
            assert (other.booking is not None) is takes_bookings(dataset), scenario.id

    for scenario in by_kind(dataset, AutotestScenarioKind.DATA_EXFILTRATION):
        assert scenario.setup is not None and scenario.setup.other_customer
        other_name = scenario.setup.other_customer.name.split()[0]

        assert other_name in scenario.expect.forbidden, scenario.id
