"""
The DPA names every provider personal data reaches: when the platform
gains one (a language model, a bot check, storage, a sender), section 8 of
each translation must list it, or the documents contradict the product.
"""

import re
from pathlib import Path

import pytest

LEGAL_DIRECTORY: Path = Path(__file__).resolve().parents[2] / "docs" / "legal"
SECTION_8: re.Pattern[str] = re.compile(
    r"^## 8\..*?(?=^## 9\.)", re.MULTILINE | re.DOTALL
)
# Names that stay the same in every translation (company and product names).
SUB_PROCESSORS: tuple[str, ...] = (
    "OpenAI",
    "Anthropic",
    "ElevenLabs",
    "Zadarma",
    "Meta Platforms Ireland",
    "Telegram",
    "Flitt",
    "Langfuse",
    "Sentry",
    "Render",
    "Google Calendar",
    "Cloudflare (Turnstile)",
    "S3",
    "SMTP",
    "Twilio",
    "Firebase Cloud Messaging",
)


@pytest.mark.parametrize("path", sorted(LEGAL_DIRECTORY.glob("dpa-*.md")), ids=str)
def test_every_translation_lists_every_sub_processor(path: Path) -> None:
    section = SECTION_8.search(path.read_text(encoding="utf-8"))

    assert section is not None, path
    missing = [name for name in SUB_PROCESSORS if name not in section.group(0)]
    assert missing == [], (path.name, missing)
