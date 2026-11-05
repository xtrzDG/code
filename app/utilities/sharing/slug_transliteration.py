"""
Latin spellings of the letters of non-Latin alphabets the platform's first
countries write business names in, for public chat addresses: Georgian
(the national romanization), Cyrillic (Russian, Ukrainian, Belarusian,
Kazakh) and Armenian. Latin letters with accents lose them elsewhere
(Unicode decomposition); letters of other scripts are left out.
"""

from collections.abc import Mapping

GEORGIAN_LETTERS: Mapping[str, str] = {
    "ა": "a", "ბ": "b", "გ": "g", "დ": "d", "ე": "e", "ვ": "v", "ზ": "z",
    "თ": "t", "ი": "i", "კ": "k", "ლ": "l", "მ": "m", "ნ": "n", "ო": "o",
    "პ": "p", "ჟ": "zh", "რ": "r", "ს": "s", "ტ": "t", "უ": "u", "ფ": "p",
    "ქ": "k", "ღ": "gh", "ყ": "q", "შ": "sh", "ჩ": "ch", "ც": "ts", "ძ": "dz",
    "წ": "ts", "ჭ": "ch", "ხ": "kh", "ჯ": "j", "ჰ": "h",
}  # fmt: skip

CYRILLIC_LETTERS: Mapping[str, str] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    # Ukrainian and Belarusian.
    "і": "i", "ї": "yi", "є": "ye", "ґ": "g", "ў": "w",
    # Kazakh.
    "ә": "a", "ғ": "g", "қ": "q", "ң": "n", "ө": "o", "ұ": "u", "ү": "u",
    "һ": "h",
}  # fmt: skip

ARMENIAN_LETTERS: Mapping[str, str] = {
    "ա": "a", "բ": "b", "գ": "g", "դ": "d", "ե": "e", "զ": "z", "է": "e",
    "ը": "y", "թ": "t", "ժ": "zh", "ի": "i", "լ": "l", "խ": "kh", "ծ": "ts",
    "կ": "k", "հ": "h", "ձ": "dz", "ղ": "gh", "ճ": "ch", "մ": "m", "յ": "y",
    "ն": "n", "շ": "sh", "ո": "o", "չ": "ch", "պ": "p", "ջ": "j", "ռ": "r",
    "ս": "s", "վ": "v", "տ": "t", "ր": "r", "ց": "ts", "ւ": "v", "փ": "p",
    "ք": "k", "օ": "o", "ֆ": "f", "և": "ev",
}  # fmt: skip

# Latin letters that do not decompose into a base letter and an accent.
LATIN_SPECIAL_LETTERS: Mapping[str, str] = {
    "ß": "ss", "æ": "ae", "œ": "oe", "ø": "o", "ł": "l", "đ": "d", "ð": "d",
    "þ": "th", "ı": "i", "ə": "e",
}  # fmt: skip

LETTER_SPELLINGS: Mapping[str, str] = {
    **GEORGIAN_LETTERS,
    **CYRILLIC_LETTERS,
    **ARMENIAN_LETTERS,
    **LATIN_SPECIAL_LETTERS,
}
