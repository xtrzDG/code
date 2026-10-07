"""
scripts/run_evals.py end to end on a small dataset: record, replay, the
baseline gate, a prompt change that flags the cassettes, and the exit codes.
"""

from pathlib import Path

import pytest

from scripts.eval_harness.cli_options import parse_options
from scripts.eval_harness.scenario_player import EvalMode
from scripts.run_evals import main

DATASET: str = """
niche: hotel
business:
  name: Test Hotel
  languages: [ka, en]
  prices: {standard_room: "180"}
  answers: {check_in_time: "Check-in from 14:00, check-out until 12:00."}
scenarios:
  - id: price__en
    language: en
    kind: price_question
    item: Standard double room
    persona: {name: Emma, phone: "+447911123456"}
    customer: ["How much is the standard double room?"]
    assistant:
      - call: {get_price: {item_name: Standard double room}}
      - say: "The standard double room costs 180 GEL."
    expect: {prices: ["180"], forbidden: ["%"], handoff: false}
  - id: human__ka
    language: ka
    kind: human_request
    persona: {name: ნინო, phone: "+995555100201"}
    customer: ["ადამიანთან მინდა საუბარი."]
    assistant:
      - call:
          handoff_to_human:
            {reason: customer_request, summary: "Asks for a person.", urgency: normal}
      - say_result: customer_message
    expect: {tools: [handoff_to_human], handoff: true}
"""


def arguments(base: Path, *extra: str) -> list[str]:
    return [
        "--datasets",
        str(base / "datasets"),
        "--cassettes",
        str(base / "cassettes"),
        "--baselines",
        str(base / "baselines"),
        "--out",
        str(base / "out"),
        *extra,
    ]


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "datasets").mkdir()
    (tmp_path / "datasets" / "hotel.yaml").write_text(DATASET, encoding="utf-8")
    return tmp_path


def test_record_then_replay_with_a_baseline(
    workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(arguments(workspace, "--record", "--update-baseline")) == 0
    assert (workspace / "cassettes" / "hotel.json").exists()
    assert (workspace / "baselines" / "scripted.json").exists()

    assert main(arguments(workspace, "--require-pass")) == 0

    output = capsys.readouterr().out
    assert "PASS  hotel/price__en" in output
    assert "baseline 100.0% -> 100.0%" in output
    assert (workspace / "out" / "report.html").exists()


def test_a_changed_instruction_flags_the_cassettes(
    workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(arguments(workspace, "--record")) == 0
    path = workspace / "datasets" / "hotel.yaml"
    path.write_text(DATASET.replace("14:00", "15:00"), encoding="utf-8")

    assert main(arguments(workspace)) == 1

    assert "STALE hotel/price__en" in capsys.readouterr().out
    report = (workspace / "out" / "report.json").read_text(encoding="utf-8")
    assert "The instruction changed since the recording" in report
    assert (
        "+- Question: What time are check-in and check-out?: Check-in from 15:00"
        in (report.replace("\\n", "\n"))
    )


def test_a_failing_expectation_and_a_broken_dataset(workspace: Path) -> None:
    assert main(arguments(workspace, "--record", "--language", "en")) == 0
    path = workspace / "datasets" / "hotel.yaml"
    path.write_text(DATASET.replace('forbidden: ["%"]', 'forbidden: ["180"]'), "utf-8")

    assert main(arguments(workspace, "--language", "en")) == 0
    assert main(arguments(workspace, "--language", "en", "--require-pass")) == 1

    path.write_text("niche: [", encoding="utf-8")
    assert main(arguments(workspace)) == 2


def test_options_choose_models_and_modes(tmp_path: Path) -> None:
    replay = parse_options([])
    live = parse_options(
        ["--record", "--model", "gpt-5-mini", "--judge-model", "claude-opus-5-5"]
    )
    own_customer = parse_options(
        ["--record", "--model", "gpt-5-mini", "--customer-model", "gpt-5"]
    )

    assert replay.run.mode is EvalMode.REPLAY and replay.run.models is None
    assert live.run.models is not None
    assert (live.run.models.assistant, live.run.models.customer) == (
        "gpt-5-mini",
        "claude-opus-5-5",
    )
    assert own_customer.run.models is not None
    assert own_customer.run.models.customer == "gpt-5"
    with pytest.raises(SystemExit):
        parse_options(["--samples", "0"])
