"""Evidence of the languages written in the Devanagari script."""

from app.utilities.conversations.language_evidence.language_evidence import (
    LanguageEvidence,
    letters,
    words,
)

DEVANAGARI_LANGUAGE_EVIDENCE: dict[str, LanguageEvidence] = {
    "hi": LanguageEvidence(
        "Deva",
        None,
        frozenset(),
        words("है और के में की से को यह नमस्ते धन्यवाद कितना कल आज टेबल चाहिए"),
    ),
    "mr": LanguageEvidence(
        "Deva",
        None,
        letters("ळ"),
        words("आहे आणि च्या मध्ये नमस्कार धन्यवाद किती उद्या आज टेबल हवे"),
    ),
    "ne": LanguageEvidence(
        "Deva",
        None,
        frozenset(),
        words("छ र को मा नमस्ते धन्यवाद कति भोलि आज टेबल चाहियो"),
    ),
}
