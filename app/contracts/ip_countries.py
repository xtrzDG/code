"""The approximate country of a network address, for the device list."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import CountryCode


class IpCountryLookupAdapterContract(AdapterContract, Protocol):
    """
    An offline country database (GeoLite2-Country or a compatible .mmdb
    file at GEOIP_COUNTRY_DATABASE_PATH). Approximate by nature: a VPN, a
    mobile carrier or a company network can put a person elsewhere.
    """

    def country_of(self, ip_address: ClientIpAddress) -> CountryCode | None:
        """
        The country the database places the address in; None for a private,
        local or unknown address, and when no database is set up or it
        cannot be read (the device list then shows the address alone).
        """
        raise NotImplementedError
