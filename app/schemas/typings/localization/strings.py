"""Keep abc order."""

from base_typed_string import BaseTypedString


class CountryDisplayName(BaseTypedString):
    """Country name rendered in some display language, e.g. "Грузия"."""


class CurrencyDisplayName(BaseTypedString):
    """Currency name rendered in some display language, e.g. "Georgian Lari"."""


class FormattedMoneyText(BaseTypedString):
    """Money amount formatted for a locale, e.g. "517,00 ₾"."""


class FormattedPhoneNumber(BaseTypedString):
    """Human-readable phone number, e.g. "+995 555 12 34 56"."""


class LanguageDisplayName(BaseTypedString):
    """Language name rendered in some display language, e.g. "ქართული"."""


class LocalizedTextValue(BaseTypedString):
    """Text written in one specific language."""


class RawPhoneNumberInput(BaseTypedString):
    """
    Phone number exactly as a person typed it, before parsing.

    Example:
        raw_phone = RawPhoneNumberInput("8 (999) 123-45-67")
    """


class TimezoneDisplayName(BaseTypedString):
    """Time zone rendered for people, e.g. "Asia/Tbilisi (UTC+04:00)"."""


# Keep abc order for all non example types, if possible.
