"""
The DAST gate's command (scripts/zap_gate.py): exit codes, the error lines
GitHub shows and the Markdown summary of the job.
"""

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from scripts.zap_gate import EXIT_NEW_FINDINGS, EXIT_PASSED, EXIT_UNUSABLE, main

RULES: str = (
    "10020\tFAIL\t(Missing Anti-clickjacking Header)\n"
    "#!10055-6\tIGNORE\t(CSP: style-src unsafe-inline)"
    "\tReact renders style attributes.\n"
    "10049\tIGNORE\t(Storable)\tNever raised in these reports.\n"
    "10035\tWARN\t(Strict-Transport-Security Header Not Set)\n"
    "\n"
    "# The widget answers every origin, without credentials.\n"
    "10098\tOUTOFSCOPE\t^https?://[^/]+/widget\\.js\n"
)


def zap_alert(
    plugin_id: str, risk: int, uri: str, ref: str | None = None
) -> dict[str, Any]:
    return {
        "pluginid": plugin_id,
        "alertRef": ref or plugin_id,
        "alert": f"Rule {plugin_id}",
        "riskcode": str(risk),
        "confidence": "2",
        "instances": [{"uri": uri}],
    }


def write_report(directory: Path, name: str, *alerts: dict[str, Any]) -> Path:
    path = directory / f"{name}.json"
    path.write_text(
        json.dumps(
            {"site": [{"@name": "http://localhost:3000", "alerts": list(alerts)}]}
        ),
        encoding="utf-8",
    )
    return path


def run(
    tmp_path: Path, *reports: Path, rules: str = RULES
) -> tuple[int, str, str, str]:
    rules_path = tmp_path / "rules.tsv"
    rules_path.write_text(rules, encoding="utf-8")
    summary = tmp_path / "summary.md"
    output, errors = io.StringIO(), io.StringIO()
    with redirect_stdout(output), redirect_stderr(errors):
        code = main(
            ["--rules", str(rules_path), "--summary", str(summary), *map(str, reports)]
        )
    summary_text = summary.read_text(encoding="utf-8") if summary.exists() else ""
    return code, output.getvalue(), errors.getvalue(), summary_text


def test_reviewed_and_low_findings_pass(tmp_path: Path) -> None:
    cabinet = write_report(
        tmp_path,
        "cabinet",
        zap_alert("10055", 2, "http://localhost:3000/", ref="10055-6"),
        zap_alert("10096", 1, "http://localhost:3000/en"),
        zap_alert("10109", 0, "http://localhost:3000/"),
    )
    widget = write_report(
        tmp_path, "widget", zap_alert("10098", 2, "http://localhost:8000/widget.js")
    )

    code, output, _, summary = run(tmp_path, cabinet, widget)

    assert code == EXIT_PASSED
    assert "::error::" not in output
    assert "reviewed  cabinet: Medium 10055-6" in output
    assert "listed    cabinet: Low 10096" in output
    assert summary.startswith(
        "## ZAP baseline (cabinet, widget): passed: no new Medium or High finding"
    )
    assert (
        "| widget | Medium | 10098 Rule 10098 | 1 | `http://localhost:8000/widget.js`"
        " | The widget answers every origin, without credentials. |" in summary
    )
    assert "Reviewed exceptions this run did not raise: 10049." in summary
    assert "(listed, not failing): 1 low, 1 informational" in summary


def test_a_new_medium_finding_or_a_fail_rule_fails_the_job(tmp_path: Path) -> None:
    api = write_report(
        tmp_path,
        "api",
        zap_alert("10098", 2, "http://localhost:8000/v1/businesses/b/bookings"),
        zap_alert("10020", 1, "http://localhost:8000/v1/me"),
        zap_alert("10035", 2, "http://localhost:8000/v1/me"),
    )

    code, output, _, summary = run(tmp_path, api)

    assert code == EXIT_NEW_FINDINGS
    assert (
        "::error::New ZAP finding: api: Medium 10098 Rule 10098 (1x, e.g. http://localhost:8000/v1/businesses/b/bookings)"
        in output
    )
    assert "::error::New ZAP finding: api: Low 10020" in output
    assert (
        "::error::New ZAP finding: api: Medium 10035 Rule 10035"
        " (1x, e.g. http://localhost:8000/v1/me) .zap/rules.tsv lists 10035 as"
        " WARN: only an IGNORE with a reviewed reason accepts it." in output
    )
    assert "failed: 3 new finding(s)" in summary
    assert "### New findings (fix them, or review them into .zap/rules.tsv)" in summary


def test_unusable_rules_or_reports_stop_the_gate(tmp_path: Path) -> None:
    cabinet = write_report(tmp_path, "cabinet")
    empty = tmp_path / "api.json"
    empty.write_text('{"site": []}', encoding="utf-8")

    code, _, errors, summary = run(
        tmp_path, cabinet, rules="10049\tIGNORE\t(Storable)\n"
    )
    assert (code, summary) == (EXIT_UNUSABLE, "")
    assert (
        "::error::ZAP gate: line 1: IGNORE of rule 10049 needs the reviewed reason"
        in errors
    )

    code, _, errors, _ = run(tmp_path, cabinet, empty)
    assert code == EXIT_UNUSABLE
    assert "names no scanned site" in errors

    code, _, errors, _ = run(tmp_path, tmp_path / "missing.json")
    assert code == EXIT_UNUSABLE
    assert "not a readable ZAP JSON report" in errors
