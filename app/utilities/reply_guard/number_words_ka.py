"""
Number words of Georgian.

Georgian counts in twenties: "ორმოცი" is two twenties (40) and
"ორმოცდაათი" forty-and-ten (50), glued by "და" inside one word. Before a
noun or a postposition a number drops its final "ი" ("ორმოცდაათ ლარად",
"შვიდზე"), so each form also has that stem, and a word may end in a
case ending or a postposition.
"""

from app.utilities.reply_guard.number_word_lexicon import (
    NumberWordLexicon,
    with_stems,
)

GEORGIAN_FINAL_VOWEL: str = "ი"

GEORGIAN_NUMBER_WORDS: NumberWordLexicon = NumberWordLexicon(
    values=with_stems(
        {
            "ერთი": 1,
            "ორი": 2,
            "სამი": 3,
            "ოთხი": 4,
            "ხუთი": 5,
            "ექვსი": 6,
            "შვიდი": 7,
            "რვა": 8,
            "ცხრა": 9,
            "ათი": 10,
            "თერთმეტი": 11,
            "თორმეტი": 12,
            "ცამეტი": 13,
            "თოთხმეტი": 14,
            "თხუთმეტი": 15,
            "თექვსმეტი": 16,
            "ჩვიდმეტი": 17,
            "თვრამეტი": 18,
            "ცხრამეტი": 19,
            "ოცი": 20,
            "ორმოცი": 40,
            "სამოცი": 60,
            "ოთხმოცი": 80,
            "ასი": 100,
            "ორასი": 200,
            "სამასი": 300,
            "ოთხასი": 400,
            "ხუთასი": 500,
            "ექვსასი": 600,
            "შვიდასი": 700,
            "რვაასი": 800,
            "ცხრაასი": 900,
        },
        GEORGIAN_FINAL_VOWEL,
    ),
    multipliers=with_stems(
        {"ათასი": 1000, "მილიონი": 1_000_000},
        GEORGIAN_FINAL_VOWEL,
    ),
    joiners=frozenset({"და", "-"}),
    endings=frozenset(
        {"ზე", "ს", "ის", "ად", "ით", "ამდე", "მდე", "იდან", "დან", "ში", "თვის"}
    ),
)
