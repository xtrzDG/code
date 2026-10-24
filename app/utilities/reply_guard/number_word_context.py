"""
Words around a number written in words that make it a percentage or a
clock time ("twenty percent", "yüzde yirmi", "at nine.", "um sieben Uhr",
"الساعة السابعة"). Currency words come from CLDR (`guard_lexicon`).
"""

from app.utilities.reply_guard.hour_words import HOUR_PREFIX_WORDS, HOUR_SUFFIX_WORDS

# Words (folded: lower case) after a number that make it a percentage.
PERCENT_WORDS: frozenset[str] = frozenset(
    {
        "%",
        "٪",
        "％",
        "percent",
        "pct",
        "процент",
        "процента",
        "процентов",
        "відсоток",
        "відсотки",
        "відсотків",
        "პროცენტი",
        "პროცენტს",
        "პროცენტით",
        "პროცენტიანი",
        "prozent",
        "pourcent",
        "porciento",
        "אחוז",
        "אחוזים",
        "بالمئة",
        "بالمائة",
    }
)
# Two words after a number that make it a percentage.
PERCENT_PHRASES: frozenset[tuple[str, str]] = frozenset(
    {
        ("per", "cent"),
        ("pour", "cent"),
        ("por", "ciento"),
        ("في", "المئة"),
        ("في", "المائة"),
    }
)
# Words before a number that make it a percentage ("yüzde yirmi").
PERCENT_PREFIX_WORDS: frozenset[str] = frozenset({"yüzde", "%", "٪"})

# Words before a number that always make it a clock hour, whatever follows
# ("saat yedide gelin", "a las siete de la tarde").
STRONG_HOUR_PREFIX_WORDS: frozenset[str] = frozenset(
    {
        "saat",
        "בשעה",
        "الساعة",
        "las",
        "alle",
        "dalle",
        "um",
        "às",
        "сағат",
        "ժամը",
    }
)
# Other hour prefixes ("at", "в", "à", "until") also introduce counts and
# places ("at one of our branches"); they make a clock hour only when the
# number ends the clause or a time-of-day word follows.
WEAK_HOUR_PREFIX_WORDS: frozenset[str] = HOUR_PREFIX_WORDS - STRONG_HOUR_PREFIX_WORDS
# Words after a number that make it a clock hour.
NUMBER_WORD_HOUR_SUFFIXES: frozenset[str] = HOUR_SUFFIX_WORDS | frozenset(
    {
        "am",
        "pm",
        "a.m",
        "p.m",
        "a.m.",
        "p.m.",
        "uhr",
        "საათი",
        "საათამდე",
        "საათიდან",
        "годин",
        "години",
        "годині",
        "ранку",
        "вечора",
    }
)
# Arabic says hours as ordinals: "الساعة السابعة" (at seven o'clock).
ARABIC_HOUR_ORDINALS: dict[str, int] = {
    "الواحدة": 1,
    "الثانية": 2,
    "الثالثة": 3,
    "الرابعة": 4,
    "الخامسة": 5,
    "السادسة": 6,
    "السابعة": 7,
    "الثامنة": 8,
    "التاسعة": 9,
    "العاشرة": 10,
    "الحادية": 11,
}
ARABIC_HOUR_WORD: str = "الساعة"
# Punctuation that ends a clause after a number ("We open at nine.").
CLAUSE_END_MARKS: frozenset[str] = frozenset('.,;:!?)»”"…—–-')
