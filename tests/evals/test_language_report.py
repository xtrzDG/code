"""
What the replies of each scenario language read as (the language
confusion), on the HTML page and in the Markdown job summary of a run.
"""

from pathlib import Path

from scripts.eval_harness.baselines import build_baseline, compare_with_baseline
from scripts.eval_harness.cli_options import parse_options
from scripts.eval_harness.eval_report import EvalReport, ModelsUsed
from scripts.eval_harness.html_languages import render_language_confusion
from scripts.eval_harness.language_confusion import summarize_language_confusion
from scripts.eval_harness.report_markdown import render_markdown
from scripts.eval_harness.report_writing import write_reports
from scripts.eval_harness.run_results import SampleResult, ScenarioResult
from scripts.eval_harness.run_summary import summarize
from tests.evals.result_builders import sample, scenario


def read_as(passed: bool, *languages: str) -> SampleResult:
    played = sample(passed)
    played.reply_languages.extend(languages)
    return played


def scenarios(russian_passes: bool = False) -> list[ScenarioResult]:
    return [
        scenario("hotel", "ru", [read_as(russian_passes, "uk", "ru", "?")]),
        scenario("clinic", "pt-BR", [read_as(True, "pt", "pt")]),
        scenario("clinic", "en", [read_as(True)]),
    ]


def report(with_baseline: bool) -> EvalReport:
    played = scenarios()
    summary = summarize(played)
    baseline = build_baseline(
        summarize(scenarios(True)), scenarios(True), "gpt-5-mini", None, 1
    )
    return EvalReport(
        generated_at="2026-10-05T12:00:00+00:00",
        mode="record",
        samples=1,
        models=[ModelsUsed(niche="hotel", assistant="gpt-5-mini", customer="x")],
        summary=summary,
        baseline=(
            compare_with_baseline(baseline, summary, played) if with_baseline else None
        ),
        scenarios=played,
    )


def test_each_language_counts_what_its_replies_read_as() -> None:
    rows = summarize_language_confusion(scenarios())

    assert [
        (row.expected, row.replies, row.read_as, row.mismatched) for row in rows
    ] == [
        ("pt", 2, {"pt": 2}, 0),
        ("ru", 3, {"uk": 1, "ru": 1, "?": 1}, 1),
    ]


def test_the_page_lists_the_misread_languages_first() -> None:
    section = render_language_confusion(summarize(scenarios()))

    assert section.index("<td>ru</td>") < section.index("<td>pt</td>")
    assert "uk 1, ru 1, ? 1" in section
    assert 'class="bad">1 (33.3%)' in section
    assert render_language_confusion(summarize([])) == ""


def test_the_job_summary_shows_the_gate_criteria_and_misread_languages() -> None:
    markdown = render_markdown(report(with_baseline=True))

    assert markdown.startswith("### Evaluation: gpt-5-mini (record)")
    assert "pass^1: **66.7%** (2/3)" in markdown
    assert "**regression**" in markdown
    assert "| prices | 66.7% | -33.3 pt **regressed** |" in markdown
    assert "| language | 100.0% | +0.0 pt |" in markdown
    assert "| ru | 3 | 1 (uk 1, ru 1, ? 1) |" in markdown
    assert "Newly failing: hotel/price__ru" in markdown


def test_without_a_baseline_the_summary_says_so(tmp_path: Path) -> None:
    written = write_reports(tmp_path, report(with_baseline=False))

    assert [path.name for path in written] == [
        "report.json",
        "report.html",
        "summary.md",
    ]
    markdown = written[2].read_text(encoding="utf-8")
    assert "- no baseline for this model yet" in markdown
    assert "regressed" not in markdown


def test_the_criterion_tolerance_is_an_option() -> None:
    assert parse_options([]).criterion_tolerance == 0.03
    assert parse_options(["--criterion-tolerance", "0.1"]).criterion_tolerance == 0.1
