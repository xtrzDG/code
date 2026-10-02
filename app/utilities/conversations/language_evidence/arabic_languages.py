"""Evidence of the languages written in the Arabic script."""

from app.utilities.conversations.language_evidence.language_evidence import (
    LanguageEvidence,
    letters,
    words,
)

ARABIC_LANGUAGE_EVIDENCE: dict[str, LanguageEvidence] = {
    "ar": LanguageEvidence(
        "Arab",
        None,
        letters("ةىإؤ"),
        words(
            "في من على أن هل ما مرحبا شكرا أريد طاولة غدا اليوم كم سعر السعر لو "
            "سمحت فضلك عندكم هذا مساء الخير"
        ),
    ),
    "fa": LanguageEvidence(
        "Arab",
        None,
        letters("پچژگ"),
        words(
            "و در به از که این است را با برای سلام ممنون می خواهم میز فردا "
            "امروز چند قیمت لطفا"
        ),
    ),
    "ur": LanguageEvidence(
        "Arab",
        None,
        letters("ٹڈڑںےھ"),
        words(
            "اور میں کے کی ہے کا سے کو یہ آپ نہیں سلام شکریہ چاہیے میز کل آج "
            "کتنے قیمت براہ کرم"
        ),
    ),
}
