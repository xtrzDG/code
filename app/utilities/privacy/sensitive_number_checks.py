"""
Check digits of the numbers `sensitive_numbers` masks: a candidate is
masked only when its own checksum holds, so prices, dates, phone numbers
and booking references that merely look alike stay readable.
"""

# Countries that issue IBANs (ISO 13616 registry).
IBAN_COUNTRY_CODES: frozenset[str] = frozenset(
    (
        "AD AE AL AT AZ BA BE BG BH BI BR BY CH CR CY CZ DE DJ DK DO EE EG ES "
        "FI FK FO FR GB GE GI GL GR GT HR HU IE IL IQ IS IT JO KW KZ LB LC LI "
        "LT LU LV LY MC MD ME MK MN MR MT MU NI NL NO OM PK PL PS PT QA RO RS "
        "RU SA SC SD SE SI SK SM SO ST SV TL TN TR UA VA VG XK YE"
    ).split()
)
MIN_IBAN_LENGTH: int = 15
MAX_IBAN_LENGTH: int = 34
MIN_CARD_DIGITS: int = 13
MAX_CARD_DIGITS: int = 19
# The Italian tax code's check letter: the values of the characters in odd
# positions (1st, 3rd, ...), digits as the letter of the same rank.
TAX_CODE_ODD_VALUES: dict[str, int] = dict(
    zip(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        (1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11, 3, 6, 8, 12, 14)
        + (16, 10, 22, 25, 24, 23),
        strict=True,
    )
)
TAX_CODE_DIGIT_LETTERS: str = "ABCDEFGHIJ"
TAX_CODE_LENGTH: int = 16
ALPHABET_SIZE: int = 26


def passes_luhn(digits: str) -> bool:
    """The Luhn (mod 10) check every payment card number carries."""

    total: int = 0
    for position, character in enumerate(reversed(digits)):
        value: int = int(character)
        if position % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value

    return total % 10 == 0


def is_card_number(digits: str) -> bool:
    """13 to 19 digits, not starting with 0 (cards never do), Luhn-valid."""

    return (
        MIN_CARD_DIGITS <= len(digits) <= MAX_CARD_DIGITS
        and digits.isdigit()
        and not digits.startswith("0")
        and passes_luhn(digits)
    )


def is_iban(candidate: str) -> bool:
    """An IBAN of a registered country whose mod-97 check holds."""

    compact: str = "".join(candidate.split()).upper()
    if not (MIN_IBAN_LENGTH <= len(compact) <= MAX_IBAN_LENGTH):
        return False

    if compact[:2] not in IBAN_COUNTRY_CODES or not compact[2:4].isdigit():
        return False

    if not compact.isalnum() or not compact.isascii():
        return False

    rearranged: str = compact[4:] + compact[:4]
    number: str = "".join(
        str(ord(character) - ord("A") + 10) if character.isalpha() else character
        for character in rearranged
    )
    return int(number) % 97 == 1


def is_italian_tax_code(candidate: str) -> bool:
    """A codice fiscale whose last letter is its check letter."""

    code: str = candidate.upper()
    if len(code) != TAX_CODE_LENGTH or not code.isascii() or not code.isalnum():
        return False

    total: int = 0
    for position, character in enumerate(code[:-1]):
        letter: str = (
            TAX_CODE_DIGIT_LETTERS[int(character)] if character.isdigit() else character
        )
        total += (
            TAX_CODE_ODD_VALUES[letter]
            if position % 2 == 0
            else ord(letter) - ord("A")
        )

    return code[-1] == chr(ord("A") + total % ALPHABET_SIZE)
