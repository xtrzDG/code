"""
The records of processing (docs/legal/records-of-processing.md, PRIV-03)
stay current: reviewed within six months, the DPO assessment is linked,
every sub-processor of the DPA's list is named, and the pull request
template asks for the records when personal data or vendors change.
"""

import re
from datetime import UTC, date, datetime, timedelta

from app.registries.legal.subprocessor_registry import SubprocessorRegistry
from tests.legal.governance_documents import missing_paths, read

RECORDS: str = "docs/legal/records-of-processing.md"
LONGEST_GAP: timedelta = timedelta(days=184)
# How the records name each sub-processor of app/registries/legal/.
NAMED_AS: dict[str, str] = {
    "openai": "OpenAI",
    "openai_knowledge_search": "embeddings",
    "elevenlabs": "ElevenLabs",
    "zadarma": "Zadarma",
    "meta": "Meta",
    "telegram": "Telegram",
    "flitt": "Flitt",
    "stripe": "Stripe",
    "langfuse": "Langfuse",
    "sentry": "Sentry",
    "render": "Render",
    "google_calendar": "Google Calendar",
    "anthropic": "Anthropic",
    "anthropic_quality_review": "Quality sampling",
    "cloudflare_turnstile": "Cloudflare",
    "object_storage": "object storage",
    "email": "e-mail provider",
    "twilio": "Twilio",
    "web_push": "web push",
}


def test_the_records_were_reviewed_within_six_months() -> None:
    match = re.search(r"^Reviewed: ([0-9]{4}-[0-9]{2}-[0-9]{2})\.", read(RECORDS), re.M)
    today = datetime.now(UTC).date()

    assert match is not None
    reviewed = date.fromisoformat(match.group(1))
    assert reviewed <= today, "a review cannot be dated ahead"
    assert today - reviewed <= LONGEST_GAP, "review the records of processing"


def test_every_sub_processor_is_in_the_records() -> None:
    keys = {str(entry.key) for entry in SubprocessorRegistry().list_entries()}
    text = read(RECORDS)

    assert keys == set(NAMED_AS), "say how the records name the new sub-processor"
    assert sorted(key for key, name in NAMED_AS.items() if name not in text) == []


def test_the_dpo_assessment_and_the_review_step_are_linked() -> None:
    assert "`docs/security/regulatory-register.md`" in read(RECORDS)
    assert "`docs/legal/records-of-processing.md`" in read(
        ".github/pull_request_template.md"
    )
    assert missing_paths(read(RECORDS)) == []
