"""Keep abc order.

Constrained localization primitives shared by every country and language.
"""

from base_typed_string import BaseConstrainedTypedString


class CallForwardingDialCode(BaseConstrainedTypedString):
    """
    GSM supplementary-service code a person dials to set or cancel forwarding.

    Example:
        no_answer = CallForwardingDialCode("**61*+995322123456#")
        cancel_all = CallForwardingDialCode("##002#")
    """

    min_length = 4
    max_length = 32
    pattern = r"^[*#]{1,2}[0-9]{2,3}(\*\+?[0-9]{4,15})?(\*\*[0-9]{1,2})?#$"


class CallForwardingDialCodeTemplate(BaseConstrainedTypedString):
    """
    Dial code with an optional "{number}" placeholder for the target number.

    Example:
        no_answer = CallForwardingDialCodeTemplate("**61*{number}#")
    """

    min_length = 4
    max_length = 32
    pattern = r"^[*#]{1,2}[0-9]{2,3}(\*\{number\})?(\*\*[0-9]{1,2})?#$"


class CountryCode(BaseConstrainedTypedString):
    """
    ISO 3166-1 alpha-2 country code in upper case.

    Example:
        georgia = CountryCode("GE")
    """

    min_length = 2
    max_length = 2
    pattern = r"^[A-Z]{2}$"


class CurrencyCode(BaseConstrainedTypedString):
    """
    ISO 4217 alphabetic currency code.

    Example:
        lari = CurrencyCode("GEL")
    """

    min_length = 3
    max_length = 3
    pattern = r"^[A-Z]{3}$"


class E164PhoneNumber(BaseConstrainedTypedString):
    """
    Phone number in canonical E.164 form: "+" and up to 15 digits.

    Only values produced by the phone number parser (validated against the
    numbering plan of the detected country) should be constructed.

    Example:
        venue_phone = E164PhoneNumber("+995555123456")
    """

    min_length = 8
    max_length = 16
    pattern = r"^\+[1-9][0-9]{6,14}$"


class EmergencyNumber(BaseConstrainedTypedString):
    """
    Short emergency service number dialled inside a country.

    Example:
        europe_emergency = EmergencyNumber("112")
    """

    min_length = 2
    max_length = 6
    pattern = r"^[0-9]{2,6}$"


class LanguageTag(BaseConstrainedTypedString):
    """
    BCP 47 language tag limited to language, optional script and region.

    Examples: "ka", "ru", "en", "pt-BR", "zh-Hant", "sr-Latn-RS".
    """

    min_length = 2
    max_length = 16
    pattern = r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-([A-Z]{2}|[0-9]{3}))?$"


class ScriptCode(BaseConstrainedTypedString):
    """
    ISO 15924 script code.

    Example:
        georgian_script = ScriptCode("Geor")
    """

    min_length = 4
    max_length = 4
    pattern = r"^[A-Z][a-z]{3}$"


class TimezoneName(BaseConstrainedTypedString):
    """
    IANA time zone name such as "Asia/Tbilisi" or "UTC".

    The pattern checks the shape only; existence is checked against the IANA
    database by the time zone utility before construction.
    """

    min_length = 2
    max_length = 64
    pattern = r"^[A-Za-z][A-Za-z0-9_+\-]*(/[A-Za-z0-9_+\-]+){0,2}$"


# Keep abc order for all non example types, if possible.
