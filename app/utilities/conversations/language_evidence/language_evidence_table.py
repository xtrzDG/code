"""
Evidence for telling languages apart in short customer messages.

Writing systems are recognized by Unicode blocks. Languages that share a
script are told apart by letters (an alphabet, letters that only this
language uses) and by short lists of very frequent words, including the
words of a typical first message to a business (greetings, "table",
"tomorrow", "how much"). No external model is involved, so detection is
instant and deterministic.
"""

from app.utilities.conversations.language_evidence.arabic_languages import (
    ARABIC_LANGUAGE_EVIDENCE,
)
from app.utilities.conversations.language_evidence.cyrillic_languages import (
    CYRILLIC_LANGUAGE_EVIDENCE,
)
from app.utilities.conversations.language_evidence.devanagari_languages import (
    DEVANAGARI_LANGUAGE_EVIDENCE,
)
from app.utilities.conversations.language_evidence.language_evidence import (
    LanguageEvidence,
)
from app.utilities.conversations.language_evidence.latin_languages import (
    LATIN_LANGUAGE_EVIDENCE,
)

# Every language the detector knows, by script, in a fixed order.
LANGUAGE_EVIDENCE: dict[str, LanguageEvidence] = {
    **LATIN_LANGUAGE_EVIDENCE,
    **CYRILLIC_LANGUAGE_EVIDENCE,
    **ARABIC_LANGUAGE_EVIDENCE,
    **DEVANAGARI_LANGUAGE_EVIDENCE,
}
