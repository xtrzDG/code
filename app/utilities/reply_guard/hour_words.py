"""Words around a bare number that make it a clock hour, in several languages."""

# Words around a bare number that make it a clock hour ("at 7", "в 7",
# "um 7 Uhr", "7-ზე", "à 7 heures"). CLDR has no prepositions, so this is a
# short curated list; words that also introduce counts ("на", "до", "a")
# are left out on purpose.
HOUR_PREFIX_WORDS: frozenset[str] = frozenset(
    {
        "@",
        "after",
        "alle",
        "around",
        "at",
        "before",
        "bis",
        "dalle",
        "desde",
        "dès",
        "gegen",
        "hacia",
        "hasta",
        "las",
        "till",
        "um",
        "until",
        "vers",
        "verso",
        "à",
        "às",
        "в",
        "во",
        "к",
        "ко",
        "около",
        "после",
        "сағат",
        "ժամը",
        "בשעה",
        "الساعة",
        "saat",
    }
)
HOUR_SUFFIX_WORDS: frozenset[str] = frozenset(
    {
        "h",
        "heure",
        "heures",
        "hora",
        "horas",
        "o'clock",
        "o’clock",
        "ora",
        "ore",
        "uhr",
        "вечера",
        "дня",
        "ночи",
        "утра",
        "час",
        "часа",
        "часов",
        "ժամին",
        "ზე",
        "საათზე",
        "საათისთვის",
    }
)
