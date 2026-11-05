"""
Number words of Hebrew and Arabic.

Both write "and" (ו, و) and a few prepositions and the article (ב, ל, ה,
ال, ب) as prefixes of the next word, and say teens as a unit followed by
"ten" ("חמש עשרה", "خمسة عشر"); Arabic puts units before tens ("خمسة
وعشرون"). Arabic words are folded first: every alef form reads as "ا".
"""

from app.utilities.reply_guard.number_word_lexicon import NumberWordLexicon


def forms(value: int, *words: str) -> dict[str, int]:
    return dict.fromkeys(words, value)


HEBREW_NUMBER_WORDS: NumberWordLexicon = NumberWordLexicon(
    values={
        **forms(1, "אחד", "אחת"),
        **forms(2, "שניים", "שתיים", "שני", "שתי", "שנים", "שתים"),
        **forms(3, "שלושה", "שלוש", "שלושת", "שלש"),
        **forms(4, "ארבעה", "ארבע", "ארבעת"),
        **forms(5, "חמישה", "חמש", "חמשת"),
        **forms(6, "שישה", "שש", "ששת"),
        **forms(7, "שבעה", "שבע", "שבעת"),
        **forms(8, "שמונה", "שמונת"),
        **forms(9, "תשעה", "תשע", "תשעת"),
        **forms(10, "עשרה", "עשר", "עשרת"),
        **forms(20, "עשרים"),
        **forms(30, "שלושים"),
        **forms(40, "ארבעים"),
        **forms(50, "חמישים"),
        **forms(60, "שישים"),
        **forms(70, "שבעים"),
        **forms(80, "שמונים"),
        **forms(90, "תשעים"),
        **forms(100, "מאה"),
        **forms(200, "מאתיים"),
        **forms(2000, "אלפיים"),
    },
    multipliers={
        **forms(100, "מאות"),
        **forms(1000, "אלף", "אלפים", "אלפי"),
        **forms(1_000_000, "מיליון"),
    },
    leading_prefixes=frozenset({"ו", "ב", "ל", "ה", "מ", "ש", "כ"}),
    teen_words=frozenset({"עשר", "עשרה"}),
)

ARABIC_NUMBER_WORDS: NumberWordLexicon = NumberWordLexicon(
    values={
        **forms(1, "واحد", "واحدة", "احد", "احدى"),
        **forms(2, "اثنان", "اثنين", "اثنتان", "اثنتين", "اثنا", "اثني"),
        **forms(3, "ثلاثة", "ثلاث"),
        **forms(4, "اربعة", "اربع"),
        **forms(5, "خمسة", "خمس"),
        **forms(6, "ستة", "ست"),
        **forms(7, "سبعة", "سبع"),
        **forms(8, "ثمانية", "ثماني", "ثمان"),
        **forms(9, "تسعة", "تسع"),
        **forms(10, "عشرة", "عشر"),
        **forms(20, "عشرون", "عشرين"),
        **forms(30, "ثلاثون", "ثلاثين"),
        **forms(40, "اربعون", "اربعين"),
        **forms(50, "خمسون", "خمسين"),
        **forms(60, "ستون", "ستين"),
        **forms(70, "سبعون", "سبعين"),
        **forms(80, "ثمانون", "ثمانين"),
        **forms(90, "تسعون", "تسعين"),
        **forms(200, "مائتان", "مائتين", "مئتان", "مئتين"),
        **forms(2000, "الفان", "الفين"),
    },
    # "مائة" scales the unit before it: "ثلاثمائة" is 300.
    multipliers={
        **forms(100, "مائة", "مئة"),
        **forms(1000, "الف", "الاف"),
        **forms(1_000_000, "مليون", "ملايين"),
    },
    leading_prefixes=frozenset(
        {"و", "ب", "ل", "ف", "ال", "بال", "وال", "لل", "فال", "وب", "ول"}
    ),
    teen_words=frozenset({"عشر", "عشرة"}),
    is_unit_before_tens=True,
)
