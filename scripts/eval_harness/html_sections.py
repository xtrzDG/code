"""Sections of the HTML report (see html_report)."""

from collections.abc import Sequence
from html import escape

from scripts.eval_harness.baselines import BaselineDiff
from scripts.eval_harness.run_results import SampleResult, ScenarioResult
from scripts.eval_harness.run_summary import RunSummary

GOOD_RATE: float = 0.95
FAIR_RATE: float = 0.8


def percent(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def rate_class(rate: float) -> str:
    if rate >= GOOD_RATE:
        return "good"

    return "warn" if rate >= FAIR_RATE else "bad"


def change_cell(delta: float) -> str:
    css: str = "bad" if delta < 0 else "good"
    return f'<td class="{css}">{delta * 100:+.1f} pt</td>'


def bar(rate: float) -> str:
    return f'<div class="bar"><span style="width:{rate * 100:.1f}%"></span></div>'


def tile(value: str, label: str, css: str = "") -> str:
    return (
        f'<div class="tile"><div class="value {css}">{escape(value)}</div>'
        f'<div class="label">{escape(label)}</div></div>'
    )


def render_tiles(summary: RunSummary) -> str:
    tiles: list[str] = [
        tile(percent(summary.pass_rate), "pass^k", rate_class(summary.pass_rate)),
        tile(percent(summary.pass_at_1), "pass@1"),
        tile(f"{summary.passed_count}/{summary.scenario_count}", "scenarios passed"),
        tile(
            str(summary.stale_count),
            "stale cassettes",
            "bad" if summary.stale_count else "",
        ),
        tile(f"${summary.cost_usd:.4f}", "list-price cost"),
        tile(f"{summary.latency_p50_ms} ms", "model time p50 per turn"),
        tile(f"{summary.latency_p95_ms} ms", "model time p95 per turn"),
    ]
    return f'<div class="tiles">{"".join(tiles)}</div>'


def render_baseline(diff: BaselineDiff | None) -> str:
    if diff is None:
        return '<h2>Baseline</h2><p class="meta">No baseline for this model yet.</p>'

    verdict: str = (
        '<span class="badge bad">regression</span>'
        if diff.is_regression
        else '<span class="badge good">within tolerance</span>'
    )
    rows: list[str] = [
        f"<tr><td>Pass rate</td><td>{percent(diff.baseline_pass_rate)}</td>"
        f"<td>{percent(diff.pass_rate)}</td>"
        f"{change_cell(diff.delta)}</tr>"
    ]
    rows.extend(
        f"<tr><td>{escape(criterion)}</td><td></td><td></td>{change_cell(delta)}</tr>"
        for criterion, delta in diff.criteria_deltas.items()
        if delta
    )
    flipped: str = "".join(
        [
            list_block("Newly failing", diff.newly_failing, "bad"),
            list_block("Newly passing", diff.newly_passing, "good"),
        ]
    )
    return (
        f"<h2>Baseline {verdict}</h2>"
        f'<p class="meta">{diff.compared_scenarios} shared scenarios, tolerance '
        f"{diff.tolerance * 100:.1f} pt</p>"
        '<div class="panel"><table><tr><th></th><th>Baseline</th><th>Now</th>'
        f"<th>Change</th></tr>{''.join(rows)}</table></div>{flipped}"
    )


def list_block(title: str, keys: Sequence[str], css: str) -> str:
    if not keys:
        return ""

    items: str = "".join(f"<li><code>{escape(key)}</code></li>" for key in keys)
    return f'<p class="{css}"><b>{escape(title)}</b></p><ul>{items}</ul>'


def render_criteria(summary: RunSummary) -> str:
    rows: str = "".join(
        f"<tr><td>{escape(item.criterion)}</td><td>{item.passed}/{item.checked}</td>"
        f'<td class="{rate_class(item.rate)}">{percent(item.rate)}</td>'
        f"<td>{bar(item.rate)}</td></tr>"
        for item in summary.criteria
    )
    return (
        '<h2>Deterministic criteria</h2><div class="panel"><table>'
        "<tr><th>Criterion</th><th>Passed</th><th>Rate</th><th></th></tr>"
        f"{rows}</table></div>"
    )


def render_judge(summary: RunSummary) -> str:
    if not summary.judge_averages:
        return ""

    rows: str = "".join(
        f"<tr><td>{escape(criterion)}</td><td>{average:.2f} / 5</td></tr>"
        for criterion, average in summary.judge_averages.items()
    )
    return (
        '<h2>Judge</h2><div class="panel"><table>'
        f"<tr><th>Criterion</th><th>Average</th></tr>{rows}</table></div>"
    )


def render_matrix(summary: RunSummary) -> str:
    languages: list[str] = sorted({group.language for group in summary.groups})
    niches: list[str] = sorted({group.niche for group in summary.groups})
    cells: dict[tuple[str, str], str] = {
        (group.niche, group.language): (
            f'<td class="{rate_class(group.pass_rate)}">'
            f"{group.passed}/{group.scenarios}</td>"
        )
        for group in summary.groups
    }
    header: str = "".join(f"<th>{escape(language)}</th>" for language in languages)
    rows: str = "".join(
        f"<tr><td>{escape(niche)}</td>"
        + "".join(cells.get((niche, language), "<td></td>") for language in languages)
        + "</tr>"
        for niche in niches
    )
    return (
        '<h2>Niches and languages</h2><div class="panel"><table>'
        f"<tr><th>Niche</th>{header}</tr>{rows}</table></div>"
    )


def render_scenarios(scenarios: Sequence[ScenarioResult]) -> str:
    ordered: list[ScenarioResult] = sorted(
        scenarios, key=lambda scenario: (scenario.is_passed, scenario.key)
    )
    return "<h2>Scenarios</h2>" + "".join(render_scenario(item) for item in ordered)


def render_scenario(scenario: ScenarioResult) -> str:
    badge: str = (
        '<span class="badge good">pass</span>'
        if scenario.is_passed
        else '<span class="badge warn">stale</span>'
        if scenario.is_stale
        else '<span class="badge bad">fail</span>'
    )
    samples: str = "".join(render_sample(sample) for sample in scenario.samples)
    return (
        f"<details><summary>{badge}<code>{escape(scenario.key)}</code>"
        f'<span class="meta">{escape(scenario.kind)} &middot; '
        f"{escape(scenario.language)}</span></summary>"
        f'<div class="body">{samples}</div></details>'
    )


def render_sample(sample: SampleResult) -> str:
    failed: list[str] = [
        f"<li><b>{escape(result.criterion.value)}</b>: "
        + escape(" ".join(str(note) for note in result.notes))
        + "</li>"
        for result in sample.criteria
        if not result.is_passed
    ]
    if sample.error:
        failed.append(f"<li><b>error</b>: {escape(sample.error)}</li>")

    stale: str = "".join(
        f'<pre class="warn">{escape(reason)}</pre>' for reason in sample.stale_reasons
    )
    judge: str = (
        ""
        if sample.judge is None
        else "<p>Judge: "
        + escape(
            ", ".join(f"{name} {score}" for name, score in sample.judge.scores.items())
        )
        + "".join(f"<br>&ndash; {escape(note)}" for note in sample.judge.notes)
        + "</p>"
    )
    lines: str = "".join(
        f'<div class="line"><b>{escape(line.author)}</b>{escape(line.text)}</div>'
        for line in sample.transcript
    )
    tools: str = "".join(f"<pre>{escape(call)}</pre>" for call in sample.tool_calls)
    return (
        f'<p class="meta">Sample {sample.sample_index + 1}</p>'
        + (f'<ul class="bad">{"".join(failed)}</ul>' if failed else "")
        + stale
        + judge
        + lines
        + tools
    )
