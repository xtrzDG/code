"""
The datasets exercise the whole assistant: every tool it can call in a
chat is expected by at least one scenario, and every kind of scenario (the
autotest kinds and the flows only the evaluations play) is played at least
once. A new tool or kind fails here until a scenario covers it.
"""

from app.schemas.constants.assistants import AssistantToolName, AutotestScenarioKind
from app.schemas.constants.evaluations import EvalFlowKind
from app.utilities.conversations.tool_selection import with_decline_recording
from scripts.eval_harness.dataset_models import EvalDataset, ScenarioKind
from tests.evals.test_dataset_files import load_all

# The scenarios are chats (the owner's test chat, WhatsApp). A tool only a
# call offers (tool_selection.RECORDED_CHANNELS: decline_recording) is never
# offered to them; tests/calls/test_declined_recordings.py covers it.
CALL_ONLY_TOOLS: frozenset[AssistantToolName] = frozenset(with_decline_recording([]))


def expected_tools(datasets: list[EvalDataset]) -> set[AssistantToolName]:
    names: set[AssistantToolName] = set()
    for dataset in datasets:
        for scenario in dataset.scenarios:
            for tool in scenario.expect.tools:
                names.update(tool if isinstance(tool, dict) else {tool})

    return names


def played_kinds(datasets: list[EvalDataset]) -> set[ScenarioKind]:
    return {scenario.kind for dataset in datasets for scenario in dataset.scenarios}


def test_every_tool_is_expected_by_a_scenario() -> None:
    missing = set(AssistantToolName) - CALL_ONLY_TOOLS - expected_tools(load_all())

    assert not missing, sorted(missing)


def test_the_call_only_tools_are_the_ones_chats_never_offer() -> None:
    # Only what the chat scenarios cannot be offered leaves the check above.
    assert {AssistantToolName.DECLINE_RECORDING} == CALL_ONLY_TOOLS
    assert not CALL_ONLY_TOOLS & expected_tools(load_all())


def test_every_autotest_kind_is_played() -> None:
    missing = set(AutotestScenarioKind) - played_kinds(load_all())

    assert not missing, sorted(missing)


def test_every_evaluation_flow_is_played() -> None:
    missing = set(EvalFlowKind) - played_kinds(load_all())

    assert not missing, sorted(missing)
