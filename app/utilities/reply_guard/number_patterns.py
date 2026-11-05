"""
Patterns that find numbers in any script, and the limits of their readings.

Each pattern runs on text whose digits are normalized to ASCII first.
"""

import re

SPACE: str = r"[ \t  ]"
# Letters of scripts written without spaces between words (Han, kana,
# hangul, Thai, Lao, Khmer, Myanmar) or that attach particles to the next
# word (Arabic, Hebrew): a number right after them still stands on its own
# ("ラーメンは9800円", "价格为999元", "ราคา90บาท", "بـ١٩", "ב19:00").
NO_SPACE_LETTERS: str = (
    "\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
    "\uff66-\uff9f\uac00-\ud7af\u0e00-\u0e7f\u0e80-\u0eff\u1000-\u109f"
    "\u1780-\u17ff\u0590-\u05ff\u0600-\u06ff\u0750-\u077f"
)
NOT_A_WORD_BEFORE: str = r"(?:(?<!\w)|(?<=[" + NO_SPACE_LETTERS + r"]))"
NOT_A_WORD_AFTER: str = r"(?:(?!\w)|(?=[" + NO_SPACE_LETTERS + r"]))"
# A date or phone never continues a word, a number, a path or a time.
DATE_BOUNDARY: str = r"(?<![.,/:+\-])" + NOT_A_WORD_BEFORE
# A number may follow a dash ("12-15", "18–25 GEL"), never a word or a path.
NUMBER_BOUNDARY: str = r"(?<![.,/:+])" + NOT_A_WORD_BEFORE
ISO_DATE_PATTERN: re.Pattern[str] = re.compile(
    DATE_BOUNDARY + r"(\d{4})([-/.])(\d{1,2})\2(\d{1,2})(?!\d)"
)
CJK_DATE_PATTERN: re.Pattern[str] = re.compile(
    r"(?:(\d{4})\s*[年년]\s*)?(\d{1,2})\s*[月월]\s*(\d{1,2})\s*[日일号]"
)
NUMERIC_DATE_WITH_YEAR_PATTERN: re.Pattern[str] = re.compile(
    DATE_BOUNDARY
    + r"(\d{1,2})([./\-])(\d{1,2})\2(\d{4}|\d{2})(?![.,/\-]\d)"
    + NOT_A_WORD_AFTER
)
SLASH_DATE_PATTERN: re.Pattern[str] = re.compile(
    DATE_BOUNDARY + r"(\d{1,2})/(\d{1,2})(?!/|[.,]\d)" + NOT_A_WORD_AFTER
)
MERIDIEM: str = SPACE + r"?([ap])\.?" + SPACE + r"?m\b\.?"
COLON_TIME_PATTERN: re.Pattern[str] = re.compile(
    NUMBER_BOUNDARY
    + r"(\d{1,2}):([0-5]\d)(?::[0-5]\d)?(?:"
    + MERIDIEM
    + r")?(?!:)"
    + NOT_A_WORD_AFTER,
    re.IGNORECASE,
)
MERIDIEM_TIME_PATTERN: re.Pattern[str] = re.compile(
    NUMBER_BOUNDARY + r"(1[0-2]|0?[1-9])" + MERIDIEM,
    re.IGNORECASE,
)
H_TIME_PATTERN: re.Pattern[str] = re.compile(
    NUMBER_BOUNDARY + r"([01]?\d|2[0-3])h([0-5]\d)?" + NOT_A_WORD_AFTER
)
INTERNATIONAL_PHONE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<![\w+])\+\d[\d  \-().]{5,}\d"
)
GROUPED_PHONE_PATTERN: re.Pattern[str] = re.compile(
    DATE_BOUNDARY + r"\(?\d{2,5}\)?(?:[  \-.]\d{2,4}){2,}(?![.,]\d)" + NOT_A_WORD_AFTER
)
# National numbers of 7-8 digits in two groups ("2222 3333", "612 3456"),
# common in the Gulf, Singapore and Hong Kong; never a thousands grouping,
# whose groups after the first have three digits.
TWO_GROUP_PHONE_PATTERN: re.Pattern[str] = re.compile(
    DATE_BOUNDARY + r"\d{3,4}" + SPACE + r"\d{4}(?![.,]?\d)" + NOT_A_WORD_AFTER
)
# A national number after its trunk "0" area code ("030 1234567",
# "030/1234567", "0322-123456").
TRUNK_PHONE_PATTERN: re.Pattern[str] = re.compile(
    DATE_BOUNDARY + r"0\d{1,4}[ /\-]\d{3,8}(?![.,]?\d)" + NOT_A_WORD_AFTER
)
# Lakh and crore grouping ("1,00,000", "12,34,567.50") first, then thousands
# of three digits, then a plain number. A number never ends inside a longer
# grouped number: any other grouping is read whole, as one value.
NUMBER_PATTERN: re.Pattern[str] = re.compile(
    NUMBER_BOUNDARY
    + r"(?:\d{1,2}(?:,\d{2})+,\d{3}(?:\.\d{1,2})?"
    + r"|\d{1,3}(?:[   .,'’]\d{3})+(?:[.,]\d{1,2})?"
    + r"|\d+(?:[.,]\d+)?"
    + r"|\d+(?:[.,'’]\d+)+)"
    + r"(?![.,'’]?\d)"
)
DOTTED_TIME_PATTERN: re.Pattern[str] = re.compile(r"^(\d{1,2})\.(\d{2})$")
FOLLOWING_TOKEN_PATTERN: re.Pattern[str] = re.compile(SPACE + r"?([^\s\d]{1,12})")
PRECEDING_TOKEN_PATTERN: re.Pattern[str] = re.compile(
    r"([^\s\d]{1,12})" + SPACE + r"?$"
)
LEADING_WORD_PATTERN: re.Pattern[str] = re.compile(r"[^\W\d_]+")
# "5 October", "5th of October", "5-го октября", "5. Oktober", "5 de octubre":
# an optional suffix, an optional short connector word, the month, a year.
FOLLOWING_MONTH_PATTERN: re.Pattern[str] = re.compile(
    r"^(?:\.|-?[^\W\d_]{1,3})?"
    + SPACE
    + r"*(?:[^\W\d_]{1,3}"
    + SPACE
    + r"+)?([^\W\d_]+\.?)(?:"
    + SPACE
    + r"*,?"
    + SPACE
    + r"*(\d{4}))?"
)
# "October 5", "Oct. 5th, 2026".
PRECEDING_MONTH_PATTERN: re.Pattern[str] = re.compile(r"([^\W\d_]+)\.?" + SPACE + r"+$")
# A month followed by its own day ("6 on October 5") does not date the number
# before it.
DAY_AFTER_MONTH_PATTERN: re.Pattern[str] = re.compile(
    SPACE + r"*(?:0?[1-9]|[12]\d|3[01])(?!\d)"
)
YEAR_AFTER_DAY_PATTERN: re.Pattern[str] = re.compile(
    r"^(?:st|nd|rd|th|\.)?" + SPACE + r"*,?" + SPACE + r"*(\d{4})"
)
TRAILING_PUNCTUATION: str = ".,;:!?)]}»”\"'"
LEADING_PUNCTUATION: str = "([{«“\"'"
PERCENT_SIGNS: frozenset[str] = frozenset({"%", "٪", "％"})
NOT_DATES: frozenset[str] = frozenset({"24/7"})
MIN_PHONE_DIGITS: int = 7
TWO_DIGIT_YEAR_CENTURY: int = 2000
LEAP_YEAR: int = 2000
NOON: int = 12
HOURS_PER_DAY: int = 24
MAX_DAY: int = 31
MAX_MONTH: int = 12
MAX_MINUTE: int = 59
THOUSANDS_GROUP_LENGTH: int = 3
