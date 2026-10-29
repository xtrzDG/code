"""
ops/alerts/*.yaml are the reviewed source of the platform alert rules: the
code's copy matches them field by field, every rule has a file, and every
runbook a rule links to exists.
"""

from pathlib import Path
from typing import cast

import pytest
import yaml

from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.dto.platform_alerts import PlatformAlertRule
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
ALERTS_DIRECTORY: Path = PROJECT_ROOT / "ops" / "alerts"
REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "code",
        "severity",
        "summary",
        "measure",
        "threshold",
        "unit",
        "window_minutes",
        "volume_floor",
        "source",
        "runbook",
    }
)
# Only the multi-window burn-rate rules have a second window.
OPTIONAL_FIELDS: frozenset[str] = frozenset({"short_window_minutes"})


def read_rule_files() -> dict[str, dict[str, object]]:
    rules: dict[str, dict[str, object]] = {}
    for path in sorted(ALERTS_DIRECTORY.glob("*.yaml")):
        loaded = cast(dict[str, object], yaml.safe_load(path.read_text("utf-8")))
        assert path.stem == loaded["code"], f"{path.name} names another code"
        rules[path.stem] = loaded
    return rules


def test_every_rule_of_the_code_has_its_file_and_no_file_is_extra() -> None:
    assert set(read_rule_files()) == {code.value for code in PlatformAlertCode}
    assert set(PLATFORM_ALERT_RULES) == set(PlatformAlertCode)


@pytest.mark.parametrize("code", list(PlatformAlertCode))
def test_the_code_matches_the_reviewed_rule(code: PlatformAlertCode) -> None:
    written: dict[str, object] = read_rule_files()[code.value]
    rule: PlatformAlertRule = PLATFORM_ALERT_RULES[code]

    assert REQUIRED_FIELDS <= set(written) <= REQUIRED_FIELDS | OPTIONAL_FIELDS
    assert written["severity"] == rule.severity.value
    assert written["summary"] == str(rule.summary)
    assert written["threshold"] == int(rule.threshold)
    assert written["unit"] == rule.unit.value
    assert written["window_minutes"] == int(rule.window_minutes)
    assert written["volume_floor"] == int(rule.volume_floor)
    assert written["runbook"] == str(rule.runbook)
    short_window = rule.short_window_minutes
    assert written.get("short_window_minutes") == (
        None if short_window is None else int(short_window)
    )


def test_every_linked_runbook_exists() -> None:
    for rule in PLATFORM_ALERT_RULES.values():
        assert (PROJECT_ROOT / str(rule.runbook)).is_file(), rule.runbook
