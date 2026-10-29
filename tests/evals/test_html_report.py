"""The HTML and JSON reports of a run."""

import json
from pathlib import Path

from app.schemas.constants.evaluations import EvalCriterion
from app.schemas.dto.evaluations import EvalCriterionResult
from app.schemas.typings.evaluations.strings import EvalCheckNote
from scripts.eval_harness.baselines import build_baseline, compare_with_baseline
from scripts.eval_harness.eval_report import EvalReport, ModelsUsed
from scripts.eval_harness.html_report import render_html
from scripts.eval_harness.report_writing import write_reports
from scripts.eval_harness.run_results import TranscriptLine
from scripts.eval_harness.run_summary import summarize
from tests.evals.result_builders import sample, scenario


def report(with_baseline: bool) -> EvalReport:
    failing = sample(False, judge={"language": 2})
    failing.criteria.append(
        EvalCriterionResult(
            criterion=EvalCriterion.FORBIDDEN_VALUES,
            is_passed=False,
            notes=[EvalCheckNote("A reply contains the forbidden '<b>48</b>'.")],
        )
    )
    failing.transcript.append(TranscriptLine(author="customer", text="שלום <script>"))
    failing.tool_calls.append('get_price({"item_name": "x"}) -> {}')
    stale = sample(False, stale=True, error="ignored")
    scenarios = [
        scenario("hotel", "he", [failing]),
        scenario("hotel", "en", [stale]),
        scenario("clinic", "ka", [sample(True, [120])]),
    ]
    summary = summarize(scenarios)
    all_passed = [scenario(s.niche, s.language, [sample(True)]) for s in scenarios]
    baseline = build_baseline(summarize(all_passed), all_passed, "scripted", None, 1)
    return EvalReport(
        generated_at="2026-10-05T12:00:00+00:00",
        mode="replay",
        samples=1,
        models=[
            ModelsUsed(niche="hotel", assistant="scripted", customer="x", judge="j")
        ],
        summary=summary,
        baseline=(
            compare_with_baseline(baseline, summary, scenarios)
            if with_baseline
            else None
        ),
        scenarios=scenarios,
    )


def test_the_page_escapes_text_and_shows_every_section() -> None:
    page = render_html(report(with_baseline=True))

    assert "&lt;script&gt;" in page and "<script>" not in page
    assert "&lt;b&gt;48&lt;/b&gt;" in page
    assert 'dir="auto"' in page
    for heading in (
        "Baseline",
        "Deterministic criteria",
        "Judge",
        "Niches and languages",
    ):
        assert heading in page
    assert "regression" in page
    assert "Newly failing (2)" in page
    assert "language 2" in page
    # A stale sample shows its cause, not the failures that follow from it.
    stale_part = page.rsplit("hotel/price__en", 1)[1]
    assert "changed" in stale_part.split("</details>")[0]
    assert "ignored" not in stale_part.split("</details>")[0]


def test_without_a_baseline_the_page_says_so(tmp_path: Path) -> None:
    written = write_reports(tmp_path / "out", report(with_baseline=False))

    page = written[1].read_text(encoding="utf-8")
    data = json.loads(written[0].read_text(encoding="utf-8"))
    assert "No baseline for this model yet." in page
    assert data["summary"]["scenario_count"] == 3
    assert data["models"][0]["judge"] == "j"
