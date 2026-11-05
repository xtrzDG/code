"""Countries of network addresses from an offline MaxMind (.mmdb) database."""

import ipaddress
import logging
import threading
from typing import cast

import maxminddb

from app.contracts.ip_countries import IpCountryLookupAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.platform.strings import LocalFilePath

logger: logging.Logger = logging.getLogger(__name__)

type MaxMindRecord = dict[str, object]


class MaxMindIpCountryLookupAdapter(IpCountryLookupAdapterContract):
    """
    Reads GEOIP_COUNTRY_DATABASE_PATH (GeoLite2-Country, refreshed by the
    deploy) once, on the first lookup, and keeps it open: lookups are
    memory reads, no network. Without the setting every answer is None. A
    file that is missing or not a database is reported once and treated
    as no database, so the device list still works.
    """

    def __init__(self, app_settings: AppSettings) -> None:
        self._path: LocalFilePath | None = (
            app_settings.sessions.geoip_country_database_path
        )
        self._lock: threading.Lock = threading.Lock()
        self._reader: maxminddb.Reader | None = None
        self._is_opened: bool = False

    def country_of(self, ip_address: ClientIpAddress) -> CountryCode | None:
        try:
            address = ipaddress.ip_address(str(ip_address).strip())
        except ValueError:
            return None

        if not address.is_global:
            return None

        reader: maxminddb.Reader | None = self._open()
        if reader is None:
            return None

        try:
            record: object = reader.get(address)
        except ValueError, maxminddb.InvalidDatabaseError:
            return None

        return country_of_record(record)

    def _open(self) -> maxminddb.Reader | None:
        if self._is_opened:
            return self._reader

        with self._lock:
            if not self._is_opened:
                self._reader = open_database(self._path)
                self._is_opened = True
        return self._reader


def open_database(path: LocalFilePath | None) -> maxminddb.Reader | None:
    if path is None:
        return None

    try:
        return maxminddb.open_database(str(path))
    except OSError, ValueError, maxminddb.InvalidDatabaseError:
        logger.error(
            "GEOIP_COUNTRY_DATABASE_PATH does not name a readable country "
            "database; the device list shows addresses without countries."
        )
        return None


def country_of_record(record: object) -> CountryCode | None:
    """`country.iso_code`, else `registered_country.iso_code` (GeoLite2 layout)."""

    if not isinstance(record, dict):
        return None

    fields = cast(MaxMindRecord, record)
    for key in ("country", "registered_country"):
        place: object = fields.get(key)
        if not isinstance(place, dict):
            continue
        code: object = cast(MaxMindRecord, place).get("iso_code")
        if isinstance(code, str):
            try:
                return CountryCode(code.upper())
            except ValueError:
                return None
    return None
