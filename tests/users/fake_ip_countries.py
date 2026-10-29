"""A country database in memory: the addresses tests name, and no others."""

from collections.abc import Mapping

from app.contracts.ip_countries import IpCountryLookupAdapterContract
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import CountryCode

# The home address of tests/users/access/session_steps.py is in Georgia; the
# café's is unknown to the database.
TEST_IP_COUNTRIES: Mapping[str, str] = {"203.0.113.7": "GE"}


class FixedIpCountries(IpCountryLookupAdapterContract):
    def __init__(self, countries: Mapping[str, str] | None = None) -> None:
        self._countries: dict[str, CountryCode] = {
            address: CountryCode(code) for address, code in (countries or {}).items()
        }
        self.asked: list[str] = []

    def country_of(self, ip_address: ClientIpAddress) -> CountryCode | None:
        self.asked.append(str(ip_address))
        return self._countries.get(str(ip_address))
