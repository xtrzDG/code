"""
The reviewed ZAP rules (.zap/rules.tsv) and the alerts of ZAP's JSON
reports, judged against each other for the DAST gate (scripts/zap_gate.py).

rules.tsv keeps the packaged scans' own format, one rule per line, tab
separated, so ZAP reads the same file (zap-baseline.py -c):

    <rule>  IGNORE|INFO|WARN|FAIL  (<rule name>)  [<reviewed reason>]
    <rule>  OUTOFSCOPE  <URL pattern>

<rule> is a rule id ("10098"). ZAP knows no finer key, so a rule for one
variant of a rule, by its alert reference ("10055-6", which wins over the
rule id), is written after "#!": ZAP skips it as a comment, the gate reads
it. An IGNORE needs its reason in the fourth cell and an OUTOFSCOPE (ZAP
takes the whole rest of its line as the pattern) in the comment lines right
above it: an exception nobody explained is refused. A Medium or High finding
fails unless it is IGNOREd or every one of its addresses is out of scope; a
FAIL rule fails at any risk; the rest is listed, never failed.
"""

import json
import re
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any, cast

RULE_ID_PATTERN: re.Pattern[str] = re.compile(r"^\d+$")
ALERT_REFERENCE_PATTERN: re.Pattern[str] = re.compile(r"^\d+(?:-\d+)?$")
OUT_OF_SCOPE: str = "OUTOFSCOPE"
# A rule only the gate reads: ZAP takes the line for a comment.
GATE_ONLY_PREFIX: str = "#!"
# ZAP's confidence 0: a person marked the alert a false positive.
FALSE_POSITIVE_CONFIDENCE: str = "0"


class RulesError(ValueError):
    """rules.tsv cannot be used as written."""


class ReportError(ValueError):
    """A ZAP report is missing, unreadable or names nothing it scanned."""


class RuleAction(StrEnum):
    IGNORE = "IGNORE"
    INFO = "INFO"
    WARN = "WARN"
    FAIL = "FAIL"


class Risk(IntEnum):
    INFORMATIONAL = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass(frozen=True)
class Rule:
    key: str
    action: RuleAction
    name: str
    reason: str


@dataclass(frozen=True)
class ScopeExclusion:
    """Addresses where a rule's findings were reviewed and accepted."""

    key: str
    pattern: re.Pattern[str]
    reason: str


@dataclass(frozen=True)
class ReviewedRules:
    rules: dict[str, Rule]
    exclusions: list[ScopeExclusion]

    def rule_for(self, alert: Alert) -> Rule | None:
        return self.rules.get(alert.alert_ref) or self.rules.get(alert.plugin_id)

    def exclusions_for(self, alert: Alert) -> list[ScopeExclusion]:
        keys: set[str] = {alert.alert_ref, alert.plugin_id}
        return [exclusion for exclusion in self.exclusions if exclusion.key in keys]


@dataclass(frozen=True)
class Alert:
    """One rule's finding on one scanned site of one target."""

    target: str
    site: str
    plugin_id: str
    alert_ref: str
    name: str
    risk: Risk
    uris: tuple[str, ...]

    @property
    def count(self) -> int:
        return len(self.uris)

    @property
    def example_uri(self) -> str:
        return self.uris[0] if self.uris else ""


@dataclass
class Verdict:
    failing: list[Alert] = field(default_factory=list[Alert])
    accepted: list[Alert] = field(default_factory=list[Alert])
    listed: list[Alert] = field(default_factory=list[Alert])

    @property
    def is_passing(self) -> bool:
        return not self.failing


def parse_rule_line(
    number: int, cells: list[str], comments: list[str], is_gate_only: bool
) -> Rule | ScopeExclusion:
    if len(cells) < 3 or (cells[1] != OUT_OF_SCOPE and len(cells) > 4):
        raise RulesError(f"line {number}: expected 3 or 4 tab-separated cells")
    key, action_text = cells[0], cells[1]
    key_pattern: re.Pattern[str] = (
        ALERT_REFERENCE_PATTERN if is_gate_only else RULE_ID_PATTERN
    )
    if key_pattern.fullmatch(key) is None:
        hint: str = (
            "" if is_gate_only else " (a variant goes on a line of its own after #!)"
        )
        raise RulesError(f"line {number}: {key!r} is not a rule id{hint}")

    if action_text == OUT_OF_SCOPE:
        reason: str = " ".join(comments).strip()
        if reason == "":
            raise RulesError(
                f"line {number}: OUTOFSCOPE of {key} needs its reason"
                " in a comment above"
            )
        try:
            pattern = re.compile("\t".join(cells[2:]))
        except re.error as error:
            raise RulesError(f"line {number}: {error}") from error
        return ScopeExclusion(key, pattern, reason)

    if action_text not in RuleAction.__members__:
        raise RulesError(f"line {number}: unknown action {action_text!r}")
    action = RuleAction(action_text)
    reason = cells[3].strip() if len(cells) == 4 else ""
    if action is RuleAction.IGNORE and reason == "":
        raise RulesError(
            f"line {number}: IGNORE of rule {key} needs the reviewed reason"
        )
    return Rule(key, action, cells[2].strip(), reason)


def parse_rules(text: str) -> ReviewedRules:
    rules: dict[str, Rule] = {}
    exclusions: list[ScopeExclusion] = []
    comments: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        is_gate_only: bool = line.startswith(GATE_ONLY_PREFIX)
        if line.startswith("#") and not is_gate_only:
            comments.append(line.lstrip("#").strip())
            continue
        if line.strip() == "":
            comments = []
            continue
        content: str = line.removeprefix(GATE_ONLY_PREFIX).lstrip(" ")
        parsed = parse_rule_line(number, content.split("\t"), comments, is_gate_only)
        comments = []
        if isinstance(parsed, ScopeExclusion):
            exclusions.append(parsed)
        elif parsed.key in rules:
            raise RulesError(f"line {number}: rule {parsed.key} is listed twice")
        else:
            rules[parsed.key] = parsed
    return ReviewedRules(rules, exclusions)


def read_rules(path: Path) -> ReviewedRules:
    try:
        text: str = path.read_text(encoding="utf-8")
    except OSError as error:
        raise RulesError(f"{path}: {error.strerror}") from error
    return parse_rules(text)


def alerts_of(report: dict[str, Any], target: str) -> list[Alert]:
    """Every alert of a ZAP traditional JSON report (`-J`), false positives left out."""

    sites: object = report.get("site")
    if not isinstance(sites, list) or not sites:
        raise ReportError(f"{target}: the report names no scanned site")

    alerts: list[Alert] = []
    for site in cast(list[dict[str, Any]], sites):
        site_alerts: list[dict[str, Any]] = site.get("alerts") or []
        for alert in site_alerts:
            if str(alert.get("confidence")) == FALSE_POSITIVE_CONFIDENCE:
                continue
            plugin_id: str = str(alert["pluginid"])
            instances: list[dict[str, Any]] = alert.get("instances") or []
            alerts.append(
                Alert(
                    target=target,
                    site=str(site.get("@name", "")),
                    plugin_id=plugin_id,
                    alert_ref=str(alert.get("alertRef") or plugin_id),
                    name=str(alert.get("alert") or alert.get("name") or ""),
                    risk=Risk(int(alert["riskcode"])),
                    uris=tuple(str(each.get("uri", "")) for each in instances),
                )
            )
    return alerts


def read_report(path: Path) -> list[Alert]:
    try:
        report: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ReportError(f"{path}: not a readable ZAP JSON report") from error
    if not isinstance(report, dict):
        raise ReportError(f"{path}: not a ZAP JSON report")
    try:
        return alerts_of(cast(dict[str, Any], report), path.stem)
    except ReportError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise ReportError(f"{path}: an alert misses its rule or risk") from error


def in_scope(alert: Alert, reviewed: ReviewedRules) -> Alert | None:
    """The alert on the addresses no reviewed exclusion covers (None: none left)."""

    exclusions: list[ScopeExclusion] = reviewed.exclusions_for(alert)
    if not exclusions or not alert.uris:
        return alert
    remaining: tuple[str, ...] = tuple(
        uri
        for uri in alert.uris
        if not any(each.pattern.match(uri) for each in exclusions)
    )
    if not remaining:
        return None
    return Alert(
        alert.target,
        alert.site,
        alert.plugin_id,
        alert.alert_ref,
        alert.name,
        alert.risk,
        remaining,
    )


def judge(alerts: list[Alert], reviewed: ReviewedRules) -> Verdict:
    verdict = Verdict()
    for alert in alerts:
        scoped: Alert | None = in_scope(alert, reviewed)
        if scoped is None:
            verdict.accepted.append(alert)
            continue
        rule: Rule | None = reviewed.rule_for(scoped)
        action: RuleAction | None = None if rule is None else rule.action
        if action is RuleAction.FAIL:
            verdict.failing.append(scoped)
        elif action is RuleAction.IGNORE:
            verdict.accepted.append(scoped)
        elif scoped.risk >= Risk.MEDIUM:
            verdict.failing.append(scoped)
        else:
            verdict.listed.append(scoped)
    return verdict
