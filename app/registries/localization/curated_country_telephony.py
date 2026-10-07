"""
Curated telephony and legal defaults per country.

Not legal advice: confirm each country with a local lawyer and carrier before
launch there. Sources and caveats are next to each table.
"""

from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    EmergencyNumber,
)


def build_country_codes(*country_codes: str) -> frozenset[CountryCode]:
    return frozenset(CountryCode(country_code) for country_code in country_codes)


# Emergency numbers. 112 is the default: it is the single number of the EU,
# Georgia, Armenia, Kazakhstan, Turkey, India and many others, and GSM
# handsets route it to emergency services in most networks. Entries name the
# general emergency number, or the police number where emergency services
# have separate numbers (Japan 110, Brazil 190, Israel 100).
DEFAULT_EMERGENCY_NUMBER: EmergencyNumber = EmergencyNumber("112")
CURATED_EMERGENCY_NUMBERS: dict[CountryCode, EmergencyNumber] = {
    # North America and the Caribbean.
    CountryCode("US"): EmergencyNumber("911"),
    CountryCode("CA"): EmergencyNumber("911"),
    CountryCode("MX"): EmergencyNumber("911"),
    CountryCode("PR"): EmergencyNumber("911"),
    CountryCode("VI"): EmergencyNumber("911"),
    CountryCode("GU"): EmergencyNumber("911"),
    CountryCode("AS"): EmergencyNumber("911"),
    CountryCode("MP"): EmergencyNumber("911"),
    CountryCode("BS"): EmergencyNumber("911"),
    CountryCode("BB"): EmergencyNumber("211"),
    CountryCode("BM"): EmergencyNumber("911"),
    CountryCode("KY"): EmergencyNumber("911"),
    CountryCode("DO"): EmergencyNumber("911"),
    CountryCode("JM"): EmergencyNumber("119"),
    CountryCode("TT"): EmergencyNumber("999"),
    CountryCode("HT"): EmergencyNumber("114"),
    CountryCode("CU"): EmergencyNumber("106"),
    CountryCode("AW"): EmergencyNumber("911"),
    CountryCode("CW"): EmergencyNumber("911"),
    # Central and South America.
    CountryCode("BZ"): EmergencyNumber("911"),
    CountryCode("GT"): EmergencyNumber("110"),
    CountryCode("SV"): EmergencyNumber("911"),
    CountryCode("HN"): EmergencyNumber("911"),
    CountryCode("CR"): EmergencyNumber("911"),
    CountryCode("PA"): EmergencyNumber("911"),
    CountryCode("CO"): EmergencyNumber("123"),
    CountryCode("VE"): EmergencyNumber("911"),
    CountryCode("EC"): EmergencyNumber("911"),
    CountryCode("PE"): EmergencyNumber("105"),
    CountryCode("BO"): EmergencyNumber("110"),
    CountryCode("BR"): EmergencyNumber("190"),
    CountryCode("PY"): EmergencyNumber("911"),
    CountryCode("UY"): EmergencyNumber("911"),
    CountryCode("AR"): EmergencyNumber("911"),
    CountryCode("CL"): EmergencyNumber("133"),
    # Europe outside the 112-only area.
    CountryCode("GB"): EmergencyNumber("999"),
    # Middle East and North Africa.
    CountryCode("IL"): EmergencyNumber("100"),
    CountryCode("AE"): EmergencyNumber("999"),
    CountryCode("SA"): EmergencyNumber("911"),
    CountryCode("QA"): EmergencyNumber("999"),
    CountryCode("BH"): EmergencyNumber("999"),
    CountryCode("OM"): EmergencyNumber("9999"),
    CountryCode("JO"): EmergencyNumber("911"),
    CountryCode("IR"): EmergencyNumber("110"),
    CountryCode("EG"): EmergencyNumber("122"),
    CountryCode("MA"): EmergencyNumber("19"),
    CountryCode("DZ"): EmergencyNumber("17"),
    CountryCode("TN"): EmergencyNumber("197"),
    # Sub-Saharan Africa.
    CountryCode("ZA"): EmergencyNumber("10111"),
    CountryCode("KE"): EmergencyNumber("999"),
    CountryCode("ZW"): EmergencyNumber("999"),
    # Asia and the Pacific.
    CountryCode("JP"): EmergencyNumber("110"),
    CountryCode("CN"): EmergencyNumber("110"),
    CountryCode("TW"): EmergencyNumber("110"),
    CountryCode("HK"): EmergencyNumber("999"),
    CountryCode("MO"): EmergencyNumber("999"),
    CountryCode("SG"): EmergencyNumber("999"),
    CountryCode("MY"): EmergencyNumber("999"),
    CountryCode("BD"): EmergencyNumber("999"),
    CountryCode("PK"): EmergencyNumber("15"),
    CountryCode("LK"): EmergencyNumber("119"),
    CountryCode("NP"): EmergencyNumber("100"),
    CountryCode("TH"): EmergencyNumber("191"),
    CountryCode("VN"): EmergencyNumber("113"),
    CountryCode("KH"): EmergencyNumber("117"),
    CountryCode("PH"): EmergencyNumber("911"),
    CountryCode("AU"): EmergencyNumber("000"),
    CountryCode("NZ"): EmergencyNumber("111"),
}

# One-time login codes go first through the channel people actually read.
# WhatsApp dominates personal messaging in these countries (concept: Israel
# and Kazakhstan "live in WhatsApp"); elsewhere SMS comes first.
WHATSAPP_FIRST_COUNTRIES: frozenset[CountryCode] = build_country_codes(
    "AR", "BR", "CO", "ID", "IL", "IN", "KZ", "MX", "NG", "ZA"
)
# Telegram is a mainstream messenger here and can deliver login codes
# through its verification gateway.
TELEGRAM_OTP_COUNTRIES: frozenset[CountryCode] = build_country_codes(
    "AM", "AZ", "BY", "KG", "KZ", "RU", "TJ", "UA", "UZ"
)

# Local assistant numbers buyable without paperwork. Georgia: +995 numbers
# from Zadarma (concept "Стек"); USA, Canada, UK: instant numbers at common
# voice providers. Elsewhere providers ask for an address or company papers.
LOCAL_NUMBER_AVAILABLE_COUNTRIES: frozenset[CountryCode] = build_country_codes(
    "CA", "GB", "GE", "US"
)

# Call recording needs the consent of every party, not just a notice:
# - US: about a dozen states (California, Florida, Illinois, Maryland,
#   Massachusetts, Montana, New Hampshire, Pennsylvania, Washington, ...)
#   require all-party consent (Justia, concept "Раскрытие AI");
# - DE: StGB section 201 punishes recording the non-public spoken word;
# - FR: Code penal art. 226-1 forbids recording private words without consent;
# - CH: StGB art. 179ter forbids recording a call without the other party;
# - AU: New South Wales, South Australia, Western Australia and Tasmania
#   require all-party consent.
# Everywhere else a recording notice at the start of the call is the default
# (Georgia: personal data law art. 11, as in the concept).
ALL_PARTY_CONSENT_COUNTRIES: frozenset[CountryCode] = build_country_codes(
    "AU", "CH", "DE", "FR", "US"
)

# Countries where the product is still in its pilot (concept: Georgia first).
PILOT_COUNTRIES: frozenset[CountryCode] = build_country_codes("GE")
