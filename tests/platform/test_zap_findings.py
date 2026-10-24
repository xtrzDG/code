"""
The reviewed ZAP rules and the judging of ZAP's alerts against them
(scripts/zap_findings.py): Medium and High fail unless reviewed, a FAIL
rule fails at any risk, and every exception carries its reason.
"""

from pathlib import Path
from typing import Any

import pytest

from scripts.zap_findings import (
    Alert,
    ReportError,
    Risk,
    RuleAction,
    RulesError,
    alerts_of,
    judge,
    parse_rules,
    read_report,
    read_rules,
)
from tests.platform.environment_sources import ROOT

RULES_TSV: Path = ROOT / ".zap" / "rules.tsv"
WIDGET_SCOPE: str = "^https?://[^/]+/(widget\\.js|v1/widget/)"


def zap_alert(
    plugin_id: str, risk: int, *, confidence: str = "2", ref: str | None = None
) -> dict[str, Any]:
    return {
        "pluginid": plugin_id,
        "alertRef": ref or plugin_id,
        "alert": f"Rule {plugin_id}",
        "riskcode": str(risk),
        "confidence": confidence,
        "count": "1",
        "instances": [{"uri": f"http://localhost:3000/{plugin_id}", "method": "GET"}],
    }


def report(*alerts: dict[str, Any]) -> dict[str, Any]:
    return {
        "@programName": "ZAP",
        "site": [{"@name": "http://localhost:3000", "alerts": list(alerts)}],
    }


def alert(plugin_id: str, risk: Risk, *uris: str, ref: str | None = None) -> Alert:
    return Alert(
        "cabinet",
        "http://localhost:3000",
        plugin_id,
        ref or plugin_id,
        f"Rule {plugin_id}",
        risk,
        uris or ("/",),
    )


def test_rules_are_read_with_their_reasons() -> None:
    reviewed = parse_rules(
        "# reviewed 2026-10-23\n"
        "\n"
        "10038\tFAIL\t(Content Security Policy Header Not Set)\n"
        "#!10055-6\tIGNORE\t(CSP: style-src unsafe-inline)"
        "\tReact renders style attributes.\n"
        "10027\tINFO\t(Information Disclosure - Suspicious Comments)\n"
        "\n"
        "# The widget answers every origin, without credentials.\n"
        f"10098\tOUTOFSCOPE\t{WIDGET_SCOPE}\n"
    )

    assert set(reviewed.rules) == {"10038", "10055-6", "10027"}
    assert reviewed.rules["10038"].action is RuleAction.FAIL
    assert reviewed.rules["10055-6"].reason == "React renders style attributes."
    (exclusion,) = reviewed.exclusions
    assert exclusion.key == "10098"
    assert exclusion.pattern.pattern == WIDGET_SCOPE
    assert exclusion.reason == "The widget answers every origin, without credentials."


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("10038\tFAIL\n", "3 or 4 tab-separated cells"),
        ("10038\tFAIL\t(a)\tb\tc\n", "3 or 4 tab-separated cells"),
        ("abc\tFAIL\t(a)\n", "not a rule id"),
        ("*\tOUTOFSCOPE\t.*\n", "not a rule id"),
        ("10055-6\tWARN\t(a)\n", "a variant goes on a line of its own after #!"),
        ("#!10055-x\tWARN\t(a)\n", "not a rule id"),
        ("10038\tSKIP\t(a)\n", "unknown action"),
        ("10038\tIGNORE\t(a)\n", "needs the reviewed reason"),
        ("10038\tIGNORE\t(a)\t   \n", "needs the reviewed reason"),
        ("10098\tOUTOFSCOPE\t^https://\n", "needs its reason in a comment above"),
        (
            "# reviewed\n\n10098\tOUTOFSCOPE\t^https://\n",
            "needs its reason in a comment above",
        ),
        ("# reviewed\n10098\tOUTOFSCOPE\t^https://(\n", "missing \\)"),
        ("10038\tFAIL\t(a)\n10038\tWARN\t(a)\n", "listed twice"),
    ],
)
def test_unusable_rules_are_refused(text: str, problem: str) -> None:
    with pytest.raises(RulesError, match=problem):
        parse_rules(text)


def test_alerts_are_read_without_false_positives() -> None:
    alerts = alerts_of(
        report(
            zap_alert("10038", 2),
            zap_alert("10055", 2, ref="10055-6"),
            zap_alert("10202", 2, confidence="0"),
        ),
        "cabinet",
    )

    assert [(each.plugin_id, each.alert_ref, each.risk) for each in alerts] == [
        ("10038", "10038", Risk.MEDIUM),
        ("10055", "10055-6", Risk.MEDIUM),
    ]
    assert alerts[0].count == 1
    assert alerts[0].example_uri == "http://localhost:3000/10038"
    assert alerts[0].target == "cabinet"


def test_a_report_that_scanned_nothing_proves_nothing() -> None:
    with pytest.raises(ReportError, match="names no scanned site"):
        alerts_of({"@programName": "ZAP", "site": []}, "api")


def test_unreadable_reports_are_refused(tmp_path: Path) -> None:
    broken = tmp_path / "cabinet.json"
    broken.write_text("{not json", encoding="utf-8")
    no_risk = tmp_path / "api.json"
    no_risk.write_text('{"site": [{"alerts": [{"pluginid": "1"}]}]}', encoding="utf-8")
    listed = tmp_path / "widget.json"
    listed.write_text("[]", encoding="utf-8")

    with pytest.raises(ReportError, match="not a readable ZAP JSON report"):
        read_report(broken)
    with pytest.raises(ReportError, match="misses its rule or risk"):
        read_report(no_risk)
    with pytest.raises(ReportError, match="not a ZAP JSON report"):
        read_report(listed)
    with pytest.raises(ReportError, match="not a readable"):
        read_report(tmp_path / "missing.json")


def test_medium_and_high_fail_unless_reviewed() -> None:
    reviewed = parse_rules(
        "10049\tIGNORE\t(Storable)\tReviewed: public pages.\n"
        "10020\tFAIL\t(Anti-clickjacking Header)\n"
        "10027\tWARN\t(Suspicious Comments)\n"
        "10035\tINFO\t(HSTS)\n"
    )
    verdict = judge(
        [
            alert("10049", Risk.MEDIUM),  # reviewed exception
            alert("40012", Risk.HIGH),  # new
            alert("10035", Risk.MEDIUM),  # INFO never accepts a Medium
            alert("10027", Risk.HIGH),  # nor does WARN
            alert("10020", Risk.LOW),  # FAIL at any risk
            alert("10096", Risk.LOW),  # listed only
            alert("10109", Risk.INFORMATIONAL),
        ],
        reviewed,
    )

    assert [each.plugin_id for each in verdict.failing] == [
        "40012",
        "10035",
        "10027",
        "10020",
    ]
    assert [each.plugin_id for each in verdict.accepted] == ["10049"]
    assert [each.plugin_id for each in verdict.listed] == ["10096", "10109"]
    assert not verdict.is_passing


def test_a_variant_rule_wins_over_its_rule_and_leaves_other_variants_failing() -> None:
    reviewed = parse_rules(
        "10055\tWARN\t(CSP)\n"
        "#! 10055-6\tIGNORE\t(CSP: style-src unsafe-inline)"
        "\tReact renders style attributes.\n"
    )
    verdict = judge(
        [
            alert("10055", Risk.MEDIUM, ref="10055-6"),
            alert("10055", Risk.MEDIUM, ref="10055-4"),
        ],
        reviewed,
    )

    assert [each.alert_ref for each in verdict.accepted] == ["10055-6"]
    assert [each.alert_ref for each in verdict.failing] == ["10055-4"]


def test_out_of_scope_addresses_are_accepted_and_the_rest_is_judged() -> None:
    reviewed = parse_rules(
        f"# The widget answers every origin.\n10098\tOUTOFSCOPE\t{WIDGET_SCOPE}\n"
    )
    widget_only = alert(
        "10098",
        Risk.MEDIUM,
        "http://localhost:8000/widget.js",
        "http://localhost:8000/v1/widget/b/config",
    )
    also_cabinet = alert(
        "10098",
        Risk.MEDIUM,
        "http://localhost:8000/widget.js",
        "http://localhost:3000/login",
    )

    verdict = judge([widget_only, also_cabinet], reviewed)

    assert verdict.accepted == [widget_only]
    (failing,) = verdict.failing
    assert failing.uris == ("http://localhost:3000/login",)
    assert failing.count == 1


def test_a_clean_run_passes() -> None:
    verdict = judge([alert("10096", Risk.LOW)], parse_rules(""))

    assert verdict.is_passing


def test_the_reviewed_rules_file_is_usable_and_every_exception_has_a_reason() -> None:
    reviewed = read_rules(RULES_TSV)
    ignored = [
        rule for rule in reviewed.rules.values() if rule.action is RuleAction.IGNORE
    ]
    failing = {
        key for key, rule in reviewed.rules.items() if rule.action is RuleAction.FAIL
    }
    accepted = {rule.key for rule in ignored} | {
        each.key for each in reviewed.exclusions
    }

    assert all(len(rule.reason) >= 40 for rule in ignored)
    assert all(len(each.reason) >= 40 for each in reviewed.exclusions)
    # The headers the cabinet and the API promise never go missing unnoticed:
    # clickjacking, content type sniffing, a missing policy, a leaked stack.
    assert {"10020", "10021", "10038", "90022"} <= failing
    # No exception covers what must fail, nor a whole rule of the policy
    # (only its style-src variant), nor every address.
    assert failing.isdisjoint(accepted)
    assert "10055" not in accepted
    assert all(
        each.pattern.pattern.startswith("^https?://[^/]+/")
        for each in reviewed.exclusions
    )


def test_a_missing_rules_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(RulesError, match="rules.tsv"):
        read_rules(tmp_path / "rules.tsv")
