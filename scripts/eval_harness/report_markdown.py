"""
The short Markdown summary of a run (summary.md): what the nightly
workflow puts on its job page, so a drop shows without opening the report.
"""

from scripts.eval_harness.eval_report import EvalReport


def render_markdown(report: EvalReport) -> str:
    summary = report.summary
    models: str = ", ".join(sorted({used.assistant for used in report.models}))
    lines: list[str] = [
        f"### Evaluation: {models or 'no model'} ({report.mode})",
        "",
        f"- pass^{report.samples}: **{summary.pass_rate:.1%}** "
        f"({summary.passed_count}/{summary.scenario_count}), pass@1 "
        f"{summary.pass_at_1:.1%}",
        f"- stale {summary.stale_count}, errors {summary.errored_count}, "
        f"cost ${summary.cost_usd:.4f}, model time p50 {summary.latency_p50_ms} ms, "
        f"p95 {summary.latency_p95_ms} ms",
    ]
    diff = report.baseline
    if diff is None:
        lines.append("- no baseline for this model yet")
    else:
        verdict: str = "**regression**" if diff.is_regression else "within tolerance"
        lines.append(
            f"- baseline {diff.baseline_pass_rate:.1%} -> {diff.pass_rate:.1%} "
            f"({diff.delta * 100:+.1f} pt over {diff.compared_scenarios} scenarios, "
            f"tolerance {diff.tolerance * 100:.1f} pt): {verdict}"
        )

    lines.extend(["", "| Criterion | Rate | Change |", "| --- | --- | --- |"])
    deltas: dict[str, float] = {} if diff is None else diff.criteria_deltas
    regressed: set[str] = set() if diff is None else set(diff.regressed_criteria)
    for item in summary.criteria:
        change: str = (
            f"{deltas[item.criterion] * 100:+.1f} pt"
            if item.criterion in deltas
            else ""
        )
        flag: str = " **regressed**" if item.criterion in regressed else ""
        lines.append(f"| {item.criterion} | {item.rate:.1%} | {change}{flag} |")

    misread = [row for row in summary.language_confusion if row.mismatched]
    if misread:
        lines.extend(["", "| Language | Replies | Read as another language |"])
        lines.append("| --- | --- | --- |")
        lines.extend(
            f"| {row.expected} | {row.replies} | {row.mismatched} "
            f"({', '.join(f'{name} {count}' for name, count in row.read_as.items())}) |"
            for row in misread
        )

    if diff is not None and diff.newly_failing:
        lines.extend(["", "Newly failing: " + ", ".join(diff.newly_failing[:30])])

    return "\n".join(lines) + "\n"
