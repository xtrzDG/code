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


class ForwardingTargetNumber(BaseConstrainedTypedString):
    """
    The assistant's number as a forwarding code carries it: in E.164, as
    the national digits or as the digits with the country code, whichever
    the carrier asks for.

    Example:
        verizon_target = ForwardingTargetNumber("2125550123")
        t_mobile_target = ForwardingTargetNumber("12125550123")
    """

    min_length = 4
    max_length = 16
    pattern = r"^\+?[0-9]{4,15}$"


class LanguageTag(BaseConstrainedTypedString):
    """
    BCP 47 language tag limited to language, optional script and region.

    Examples: "ka", "ru", "en", "pt-BR", "zh-Hant", "sr-Latn-RS".
    """

    min_length = 2
    max_length = 16
    pattern = r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-([A-Z]{2}|[0-9]{3}))?$"


class OwnerTextKey(BaseConstrainedTypedString):
    """
    Key of a text in the owner text catalog
    (`app/registries/localization/texts/<language>.json`): lower-case dotted
    segments from the area down to the text. A numbered last segment is one
    line of a list ("niches.restaurant.handoff_rules.2").

    Example:
        plan_name = OwnerTextKey("plans.chat.name")
    """

    min_length = 3
    max_length = 160
    pattern = r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+){1,7}$"


class PhoneNumberPrefix(BaseConstrainedTypedString):
    """
    The start of E.164 phone numbers ("+" and 1 to 15 digits): a calling
    code or a number range of one, such as a premium-rate range that login
    codes are never sent to.

    Example:
        premium_range = PhoneNumberPrefix("+4490")
    """

    min_length = 2
    max_length = 16
    pattern = r"^\+[1-9][0-9]{0,14}$"


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


class VerticalServiceDialCode(BaseConstrainedTypedString):
    """
    North American star code a person dials to set or cancel forwarding:
    "*", two digits and, for a code that takes one, the 10-digit number.

    Example:
        no_answer_or_busy = VerticalServiceDialCode("*712125550123")
        cancel_all = VerticalServiceDialCode("*73")
    """

    min_length = 3
    max_length = 13
    pattern = r"^\*[0-9]{2}([0-9]{10})?$"


class VerticalServiceDialCodeTemplate(BaseConstrainedTypedString):
    """
    Star code with an optional "{number}" placeholder for the target number.

    Example:
        no_answer_or_busy = VerticalServiceDialCodeTemplate("*71{number}")
    """

    min_length = 3
    max_length = 11
    pattern = r"^\*[0-9]{2}(\{number\})?$"


# Keep abc order for all non example types, if possible.
