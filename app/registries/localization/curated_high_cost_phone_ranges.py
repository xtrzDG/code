"""
Phone number ranges a login code is never sent to, beyond the kinds the
numbering plans mark (premium rate, shared cost, personal and universal
access numbers; see `high_cost_phone_number_registry.py`).

SMS pumping (international revenue share fraud) makes a platform send
paid messages to numbers whose operator shares the termination fee with
the fraudster. Satellite and international networks are the classic
targets: an ordinary business owner never signs in from one, and a message
there costs many times a mobile one. The phone number parser already
refuses non-geographic numbers; listing them here keeps the refusal if
that ever changes.

Add a range when the SMS provider's fraud reports name it, or set
OTP_DENIED_PHONE_PREFIXES without a release.
"""

from app.schemas.typings.localization.constrained_strings import PhoneNumberPrefix

CURATED_HIGH_COST_PHONE_PREFIXES: tuple[PhoneNumberPrefix, ...] = (
    # Inmarsat (maritime and aeronautical satellite phones).
    PhoneNumberPrefix("+870"),
    # Global Mobile Satellite Systems: Iridium, Globalstar, ICO.
    PhoneNumberPrefix("+881"),
    # International Networks: Thuraya, maritime, in-flight and M2M networks.
    PhoneNumberPrefix("+882"),
    PhoneNumberPrefix("+883"),
    # International Premium Rate Service.
    PhoneNumberPrefix("+979"),
)
