"""
Curated default time zones and currencies.

Every country with several IANA time zones has a default here: the zone of
its capital or largest business city. Single-zone countries need no entry.
Currencies come from CLDR (legal tender on the current date); entries here
settle countries where CLDR lists two tenders or is behind a changeover.
"""

from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    TimezoneName,
)

CURATED_DEFAULT_TIMEZONES: dict[CountryCode, TimezoneName] = {
    CountryCode("AR"): TimezoneName("America/Argentina/Buenos_Aires"),
    CountryCode("AU"): TimezoneName("Australia/Sydney"),
    CountryCode("BR"): TimezoneName("America/Sao_Paulo"),
    CountryCode("CA"): TimezoneName("America/Toronto"),
    CountryCode("CD"): TimezoneName("Africa/Kinshasa"),
    CountryCode("CL"): TimezoneName("America/Santiago"),
    CountryCode("CN"): TimezoneName("Asia/Shanghai"),
    CountryCode("CY"): TimezoneName("Asia/Nicosia"),
    CountryCode("DE"): TimezoneName("Europe/Berlin"),
    CountryCode("EC"): TimezoneName("America/Guayaquil"),
    CountryCode("ES"): TimezoneName("Europe/Madrid"),
    CountryCode("FM"): TimezoneName("Pacific/Pohnpei"),
    CountryCode("GE"): TimezoneName("Asia/Tbilisi"),
    CountryCode("GL"): TimezoneName("America/Nuuk"),
    CountryCode("ID"): TimezoneName("Asia/Jakarta"),
    CountryCode("KI"): TimezoneName("Pacific/Tarawa"),
    CountryCode("KZ"): TimezoneName("Asia/Almaty"),
    CountryCode("MH"): TimezoneName("Pacific/Majuro"),
    CountryCode("MN"): TimezoneName("Asia/Ulaanbaatar"),
    CountryCode("MX"): TimezoneName("America/Mexico_City"),
    CountryCode("MY"): TimezoneName("Asia/Kuala_Lumpur"),
    CountryCode("NZ"): TimezoneName("Pacific/Auckland"),
    CountryCode("PF"): TimezoneName("Pacific/Tahiti"),
    CountryCode("PG"): TimezoneName("Pacific/Port_Moresby"),
    CountryCode("PS"): TimezoneName("Asia/Hebron"),
    CountryCode("PT"): TimezoneName("Europe/Lisbon"),
    CountryCode("RU"): TimezoneName("Europe/Moscow"),
    CountryCode("UA"): TimezoneName("Europe/Kyiv"),
    CountryCode("US"): TimezoneName("America/New_York"),
    CountryCode("UZ"): TimezoneName("Asia/Tashkent"),
}
# Used only when neither CLDR nor libphonenumber maps a region to a zone.
FALLBACK_TIMEZONE: TimezoneName = TimezoneName("UTC")

CURATED_CURRENCIES: dict[CountryCode, CurrencyCode] = {
    # Bulgaria adopted the euro on 2026-01-01; the CLDR data shipped with
    # Babel 2.18 still lists the lev.
    CountryCode("BG"): CurrencyCode("EUR"),
    CountryCode("BT"): CurrencyCode("BTN"),
    CountryCode("HT"): CurrencyCode("HTG"),
    CountryCode("LS"): CurrencyCode("LSL"),
    CountryCode("NA"): CurrencyCode("NAD"),
    # Balboa exists only as coins; prices and banknotes are in US dollars.
    CountryCode("PA"): CurrencyCode("USD"),
    CountryCode("PS"): CurrencyCode("ILS"),
    CountryCode("ZW"): CurrencyCode("USD"),
}
# Used only when CLDR lists no legal tender for a region.
FALLBACK_CURRENCY: CurrencyCode = CurrencyCode("USD")
