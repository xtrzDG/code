"""
Settings → Calls shows what callers hear at the start of every call: the
cabinet's sentences (web dictionaries) are the greeting's own, word for
word, in English and Italian, so the preview never drifts from the call.
"""

import re
from pathlib import Path

import pytest

from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.calls.call_privacy_texts import CALL_PRIVACY_NOTICE_HINT
from app.utilities.conversations.assistant_texts.call_consent_texts import (
    CALL_RECORDING_CONSENT,
)
from app.utilities.conversations.assistant_texts.call_texts import (
    CALL_GREETING,
    CALL_OPERATOR_HINT,
)

DICTIONARIES: Path = (
    Path(__file__).resolve().parents[2] / "web/src/i18n/messages/sections/workspace"
)
NOTICE_TEXTS: dict[str, LocalizedText] = {
    "noticeGreeting": CALL_GREETING,
    "noticeRecorded": CALL_RECORDING_CONSENT,
    "noticeOperator": CALL_OPERATOR_HINT,
    "noticePrivacy": CALL_PRIVACY_NOTICE_HINT,
}
ENTRY: re.Pattern[str] = re.compile(r"^\s*(notice\w+): ([\"'])(.*?)\2,$", re.MULTILINE)


def cabinet_notice_texts(language: str) -> dict[str, str]:
    source: str = (DICTIONARIES / f"callSettings.{language}.ts").read_text("utf-8")
    return {match[1]: match[3] for match in ENTRY.finditer(source)}


@pytest.mark.parametrize("language", ["en", "it"])
def test_the_cabinet_shows_the_greetings_own_sentences(language: str) -> None:
    shown: dict[str, str] = cabinet_notice_texts(language)

    for key, text in NOTICE_TEXTS.items():
        assert shown.get(key) == str(text.values[LanguageTag(language)]), key
