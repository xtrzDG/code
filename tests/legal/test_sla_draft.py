"""
The SLA draft (docs/legal/drafts/sla.md, REL-01 and GOV-01) promises no
more than the platform's internal targets: the availability, RPO and RTO
it offers businesses are at most as strict as docs/operations/slo.md and
docs/operations/backup-restore.md, the call-forwarding fallback target
is the voice runbook's, and it stays a draft the API never serves.
"""

import re

from tests.legal.governance_documents import read

SLA: str = "docs/legal/drafts/sla.md"


def percent(text: str, pattern: str) -> float:
    match = re.search(pattern, text)
    assert match is not None, pattern
    return float(match.group(1))


def test_availability_is_no_stricter_than_the_internal_objectives() -> None:
    sla, slo = read(SLA), read("docs/operations/slo.md")

    chat = percent(sla, r"answers chats[^|]*\| \*\*([0-9.]+)%\*\*")
    calls = percent(sla, r"answers calls[^|]*\| \*\*([0-9.]+)%\*\*")
    assert chat <= percent(slo, r"Answered in time[^|]*\| ([0-9.]+)% of inbound")
    assert calls <= percent(slo, r"Calls answered[^|]*\| ([0-9.]+)% \|")


def test_recovery_promises_leave_a_margin_over_the_internal_targets() -> None:
    sla, backups = read(SLA), read("docs/operations/backup-restore.md")

    assert "at most **15 minutes**" in sla and "at most **4 hours**" in sla
    assert "| RPO, database lost or corrupted | 5 minutes |" in backups
    assert "| RTO, any of the above | 2 hours |" in backups
    assert "data of the last **24 hours** at most" in sla
    assert "| RPO, Render account or region lost | 24 hours |" in backups


def test_the_call_fallback_target_is_the_voice_runbooks() -> None:
    assert "**within 15 minutes**" in read(SLA)
    assert "within **15 minutes** of detection" in read(
        "docs/operations/runbooks/voice-outage.md"
    )


def test_the_sla_is_a_draft() -> None:
    assert "Draft (needs_review)" in "\n".join(read(SLA).splitlines()[:4])
