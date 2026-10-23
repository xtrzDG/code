"""
The DAST gate of .github/workflows/zap.yml: the JSON reports of ZAP's
baseline scans (cabinet, hosted chat page, widget, API) against the
reviewed rules of .zap/rules.tsv (scripts/zap_findings.py).

    uv run --no-project python -m scripts.zap_gate --rules .zap/rules.tsv \\
        --summary "$GITHUB_STEP_SUMMARY" zap/cabinet.json zap/api.json ...

Prints one line per finding and appends a Markdown table to the summary
file. Exit codes: 0 no new finding, 1 a Medium or High finding whose rule
is not IGNOREd with a reason (or any finding of a FAIL rule), 2 rules or
reports that cannot be used (an IGNORE without a reason, a missing or empty
report: a scan that reached nothing proves nothing).
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from scripts.zap_findings import (
    Alert,
    ReportError,
    ReviewedRules,
    RuleAction,
    RulesError,
    Verdict,
    judge,
    read_report,
    read_rules,
)

EXIT_PASSED: int = 0
EXIT_NEW_FINDINGS: int = 1
EXIT_UNUSABLE: int = 2


def describe(alert: Alert) -> str:
    return (
        f"{alert.target}: {alert.risk.name.title()} {alert.alert_ref} {alert.name} "
        f"({alert.count}x, e.g. {alert.example_uri})"
    )


def reason_for(alert: Alert, reviewed: ReviewedRules) -> str:
    """Why a reviewed exception accepts the alert: its scope, else its rule."""

    for exclusion in reviewed.exclusions_for(alert):
        if any(exclusion.pattern.match(uri) for uri in alert.uris):
            return exclusion.reason
    rule = reviewed.rule_for(alert)
    return "" if rule is None else rule.reason


def table(alerts: list[Alert], reviewed: ReviewedRules, with_reason: bool) -> list[str]:
    header: str = "| Target | Risk | Rule | Instances | Example |"
    divider: str = "| --- | --- | --- | ---: | --- |"
    if with_reason:
        header += " Reviewed reason |"
        divider += " --- |"
    lines: list[str] = [header, divider]
    for alert in sorted(
        alerts, key=lambda each: (-each.risk, each.target, each.plugin_id)
    ):
        row: str = (
            f"| {alert.target} | {alert.risk.name.title()} | {alert.alert_ref} "
            f"{alert.name} | {alert.count} | `{alert.example_uri}` |"
        )
        if with_reason:
            row += f" {reason_for(alert, reviewed)} |"
        lines.append(row)
    return lines


def unseen_exceptions(alerts: list[Alert], reviewed: ReviewedRules) -> list[str]:
    """Reviewed exceptions no scan of this run raised: candidates for removal."""

    seen: set[str] = {
        key for alert in alerts for key in (alert.plugin_id, alert.alert_ref)
    }
    keys: list[str] = [
        rule.key for rule in reviewed.rules.values() if rule.action is RuleAction.IGNORE
    ] + [exclusion.key for exclusion in reviewed.exclusions]
    return sorted({key for key in keys if key not in seen})


def render(verdict: Verdict, reviewed: ReviewedRules, targets: list[str]) -> str:
    every_alert: list[Alert] = verdict.failing + verdict.accepted + verdict.listed
    title: str = (
        "passed: no new Medium or High finding"
        if verdict.is_passing
        else f"failed: {len(verdict.failing)} new finding(s)"
    )
    lines: list[str] = [f"## ZAP baseline ({', '.join(targets)}): {title}", ""]
    if verdict.failing:
        lines += ["### New findings (fix them, or review them into .zap/rules.tsv)", ""]
        lines += table(verdict.failing, reviewed, with_reason=False) + [""]
    if verdict.accepted:
        lines += ["### Reviewed exceptions (.zap/rules.tsv)", ""]
        lines += table(verdict.accepted, reviewed, with_reason=True) + [""]
    if verdict.listed:
        lines += ["### Low and informational findings (listed, not failing)", ""]
        lines += table(verdict.listed, reviewed, with_reason=False) + [""]
    unseen: list[str] = unseen_exceptions(every_alert, reviewed)
    if unseen:
        lines += [
            f"Reviewed exceptions this run did not raise: {', '.join(unseen)}.",
            "",
        ]
    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.zap_gate",
        description="Fail on ZAP findings that .zap/rules.tsv has not reviewed.",
    )
    parser.add_argument("reports", nargs="+", type=Path, help="ZAP JSON reports (-J)")
    parser.add_argument(
        "--rules", type=Path, required=True, help="the reviewed rules.tsv"
    )
    parser.add_argument("--summary", type=Path, help="Markdown file to append to")
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parsed: argparse.Namespace = build_argument_parser().parse_args(arguments)
    try:
        reviewed: ReviewedRules = read_rules(parsed.rules)
        alerts: list[Alert] = [
            alert for path in parsed.reports for alert in read_report(path)
        ]
    except (RulesError, ReportError) as error:
        print(f"::error::ZAP gate: {error}", file=sys.stderr)
        return EXIT_UNUSABLE

    verdict: Verdict = judge(alerts, reviewed)
    for alert in verdict.failing:
        print(f"::error::New ZAP finding: {describe(alert)}")
    for alert in verdict.accepted:
        print(f"reviewed  {describe(alert)}")
    for alert in verdict.listed:
        print(f"listed    {describe(alert)}")

    if parsed.summary is not None:
        targets: list[str] = [path.stem for path in parsed.reports]
        with parsed.summary.open("a", encoding="utf-8") as summary:
            summary.write(render(verdict, reviewed, targets) + "\n")

    return EXIT_PASSED if verdict.is_passing else EXIT_NEW_FINDINGS


if __name__ == "__main__":
    raise SystemExit(main())
