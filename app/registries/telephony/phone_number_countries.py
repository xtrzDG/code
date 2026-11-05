"""
Where the platform rents numbers by itself, and where it does not.

SELF_SERVE: Twilio sells call-ready numbers of these kinds there without an
address or a regulatory bundle, so an owner picks one in the cabinet.
REQUIRES_DOCUMENTS: the regulator wants the business's papers (an address
in the country, a company or identity proof) before a number is rented, so
the platform team arranges it from the owner's request (Zadarma in the
Caucasus, a bundle at Twilio in the EU). Every country not listed reads as
REQUIRES_DOCUMENTS: the team checks it by hand.

The carrier search also refuses any number that needs an address
(`Exclude*AddressRequired`), so a rule that goes stale offers fewer
numbers, never one the platform cannot rent.
"""

from collections.abc import Mapping

from app.schemas.constants.phone_numbers import PhoneNumberAvailability, PhoneNumberType
from app.schemas.typings.localization.constrained_strings import CountryCode

SELF_SERVE = PhoneNumberAvailability.SELF_SERVE
DOCUMENTS = PhoneNumberAvailability.REQUIRES_DOCUMENTS

PHONE_NUMBER_COUNTRY_RULES: Mapping[
    CountryCode, Mapping[PhoneNumberType, PhoneNumberAvailability]
] = {
    # North America: local and toll-free numbers need no address.
    CountryCode("US"): {
        PhoneNumberType.LOCAL: SELF_SERVE,
        PhoneNumberType.TOLL_FREE: SELF_SERVE,
        PhoneNumberType.MOBILE: DOCUMENTS,
    },
    CountryCode("CA"): {
        PhoneNumberType.LOCAL: SELF_SERVE,
        PhoneNumberType.TOLL_FREE: SELF_SERVE,
        PhoneNumberType.MOBILE: DOCUMENTS,
    },
    # The platform's home markets: numbers come from Zadarma with the
    # business's documents (concept: "номер Zadarma +995").
    CountryCode("GE"): {kind: DOCUMENTS for kind in PhoneNumberType},
    CountryCode("AM"): {kind: DOCUMENTS for kind in PhoneNumberType},
    CountryCode("AZ"): {kind: DOCUMENTS for kind in PhoneNumberType},
    CountryCode("UA"): {kind: DOCUMENTS for kind in PhoneNumberType},
    CountryCode("KZ"): {kind: DOCUMENTS for kind in PhoneNumberType},
    CountryCode("TR"): {kind: DOCUMENTS for kind in PhoneNumberType},
    CountryCode("IL"): {kind: DOCUMENTS for kind in PhoneNumberType},
    # The EU and the UK: a regulatory bundle (an address in the country and
    # the business's registration) for every kind.
    CountryCode("IT"): {kind: DOCUMENTS for kind in PhoneNumberType},
    CountryCode("DE"): {kind: DOCUMENTS for kind in PhoneNumberType},
    CountryCode("GB"): {kind: DOCUMENTS for kind in PhoneNumberType},
    CountryCode("PL"): {kind: DOCUMENTS for kind in PhoneNumberType},
}
