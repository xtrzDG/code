"""Keep abc order."""

from base_typed_string import BaseTypedString


class PhoneNumberLocality(BaseTypedString):
    """
    The city or area a geographic number belongs to, as the carrier names it
    ("Austin", "Toronto"); toll-free and mobile numbers usually have none.
    """


class PhoneNumberRegion(BaseTypedString):
    """
    The state, province or region of a number, as the carrier names it
    ("TX", "ON").
    """


class ProviderPhoneNumberId(BaseTypedString):
    """
    The carrier's identifier of a rented number (Twilio's IncomingPhoneNumber
    SID, "PN" and 32 hex digits), used to give it back.
    """


class TwimlDocument(BaseTypedString):
    """
    The instructions a carrier's call webhook answers with (Twilio's TwiML,
    an XML document): put the caller through to a number, or hang up.
    """


class VoicePlatformPhoneNumberId(BaseTypedString):
    """
    The voice platform's identifier of an imported number (ElevenLabs'
    phone_number_id), used to assign it to the business's agent and to
    remove it.
    """


# Keep abc order for all non example types, if possible.
