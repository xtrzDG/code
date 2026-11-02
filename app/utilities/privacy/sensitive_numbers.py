"""
Payment card, bank account and identity document numbers taken out of a
text before it is stored, shown to a model, traced or logged: the platform
never keeps a card number (PCI DSS SAQ A), and nobody needs a customer's
account or ID number to book a table (GDPR data minimization).

- A payment card number: 13 to 19 digits, together or in groups separated
  by single spaces or hyphens ("4242 4242 4242 4242", "3782-822463-10005",
  digits a speech recognizer wrote one by one), that passes the Luhn check
  and does not start with 0. A phone number written the international way
  (a leading +) is not one. The digits said right after the card in the
  same run (the expiry date and the security code) go with it.
- A security code named as such ("cvv 123", "CVC: 1234", "il codice di
  sicurezza è 123").
- An IBAN of a registered country whose mod-97 check holds, grouped in
  fours or not, in capitals or not.
- An Italian tax code (codice fiscale) whose check letter holds, and a
  document number named as such ("passaporto YA1234567", "ID card
  number CA12345AB").

Prices, dates, times, party sizes, booking references and phone numbers
stay, so what was agreed stays readable. Each found number becomes a
placeholder without digits, so masking a masked text changes nothing.
"""

import re

from app.utilities.privacy.sensitive_number_checks import (
    MAX_CARD_DIGITS,
    is_card_number,
    is_iban,
    is_italian_tax_code,
)

CARD_PLACEHOLDER: str = "[card number]"
SECURITY_CODE_PLACEHOLDER: str = "[security code]"
ACCOUNT_PLACEHOLDER: str = "[account number]"
ID_NUMBER_PLACEHOLDER: str = "[id number]"
# A run of at least 13 digits with single spaces or hyphens between them. A
# run right after "+" is a phone number, one after a decimal point or
# before a decimal part (0.30000000000000004) a fraction.
DIGIT_RUN_PATTERN: re.Pattern[str] = re.compile(
    r"(?<!\d[.,])(?<![\d+])\d(?:[ \u00a0\-]?\d){12,}(?![.,]?\d)"
)
DIGIT_GROUP_SEPARATOR: re.Pattern[str] = re.compile(r"[ \u00a0\-]")
# Two letters, two check digits, then 11 to 30 letters or digits.
IBAN_CANDIDATE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<!\w)[A-Za-z]{2}\d{2}(?:[ ]?[A-Za-z0-9]){11,30}(?!\w)"
)
# Six letters (surname and name), the birth year, month letter, day and
# place (digits, or the letters that replace them in a recoded code), and
# the check letter.
TAX_CODE_PATTERN: re.Pattern[str] = re.compile(
    r"(?<!\w)[A-Za-z]{6}[0-9LMNPQRSTUVlmnpqrstuv]{2}[ABCDEHLMPRSTabcdehlmprst]"
    r"[0-9LMNPQRSTUVlmnpqrstuv]{2}[A-Za-z][0-9LMNPQRSTUVlmnpqrstuv]{3}[A-Za-z](?!\w)"
)
SECURITY_CODE_WORDS: str = (
    r"cvv2?|cvc2?|cvn|csc|security code|card code|card verification code"
    r"|codice di sicurezza|codice cvv|codice cvc|codice di verifica"
    r"|código de seguridad|code de sécurité|cryptogramme|sicherheitscode"
    r"|prüfnummer|код безопасности|cvv-код|cvc-код"
)
# The word, up to a few words of filler ("is", "on the back:"), then 3 or 4
# digits.
SECURITY_CODE_PATTERN: re.Pattern[str] = re.compile(
    rf"(?i)(?<!\w)((?:{SECURITY_CODE_WORDS})(?![^\W\d])[^\d\n]{{0,20}}?)(\d{{3,4}})(?!\d)"
)
DOCUMENT_WORDS: str = (
    r"passport(?: number| no\.?)?|passaporto|numero (?:di )?passaporto"
    r"|(?:national )?id(?:entity)? card(?: number| no\.?)?"
    r"|carta d['’ ]?identit[àa]|carta di identit[àa]|numero (?:del )?documento"
    r"|documento(?: di identit[àa])?|patente(?: di guida)?"
    r"|driv(?:ing|er'?s) licen[cs]e(?: number| no\.?)?|personalausweis|reisepass"
    r"|паспорт|pasaporte"
)
# A document word, a few characters of filler, then 5 to 20 letters and
# digits with at least one digit.
DOCUMENT_NUMBER_PATTERN: re.Pattern[str] = re.compile(
    rf"(?i)(?<!\w)((?:{DOCUMENT_WORDS})(?!\w)[^\w\n]{{0,6}}"
    r"(?:(?:is|è|e|n\.?|no\.?|nr\.?|number|numero|:)[^\w\n]{0,4})?)"
    r"(?=[A-Za-z]*\d)([A-Za-z0-9]{5,20})(?!\w)"
)
THOUSANDS_GROUP_LENGTH: int = 3


def mask_sensitive_numbers(text: str) -> str:
    """The text with card, security code, IBAN and ID numbers replaced."""

    masked: str = IBAN_CANDIDATE_PATTERN.sub(_iban_placeholder, text)
    masked = TAX_CODE_PATTERN.sub(_tax_code_placeholder, masked)
    masked = DOCUMENT_NUMBER_PATTERN.sub(rf"\1{ID_NUMBER_PLACEHOLDER}", masked)
    masked = DIGIT_RUN_PATTERN.sub(_card_placeholder, masked)
    return SECURITY_CODE_PATTERN.sub(rf"\1{SECURITY_CODE_PLACEHOLDER}", masked)


def holds_card_number(groups: list[str]) -> bool:
    """
    Whether consecutive digit groups of one run form a card number. A run
    grouped in thousands ("1 500 000 000 000") is an amount.
    """

    if len(groups) > 2 and all(
        len(group) == THOUSANDS_GROUP_LENGTH for group in groups[1:]
    ):
        return False

    for start in range(len(groups)):
        digits: str = ""
        for group in groups[start:]:
            digits += group
            if is_card_number(digits):
                return True

            if len(digits) >= MAX_CARD_DIGITS:
                break

    return False


def _card_placeholder(match: re.Match[str]) -> str:
    run: str = match.group(0)
    groups: list[str] = DIGIT_GROUP_SEPARATOR.split(run)
    return CARD_PLACEHOLDER if holds_card_number(groups) else run


def _iban_placeholder(match: re.Match[str]) -> str:
    """
    The longest IBAN at the start of the candidate, ending where a group
    ends: "IT60 X054 2811 1010 0000 0123 456 grazie" keeps " grazie".
    """

    candidate: str = match.group(0)
    end: int = len(candidate)
    while end > 0:
        if is_iban(candidate[:end]):
            return ACCOUNT_PLACEHOLDER + candidate[end:]

        end = candidate.rfind(" ", 0, end)

    return candidate


def _tax_code_placeholder(match: re.Match[str]) -> str:
    code: str = match.group(0)
    has_digit: bool = any(character.isdigit() for character in code)
    return ID_NUMBER_PLACEHOLDER if has_digit and is_italian_tax_code(code) else code
