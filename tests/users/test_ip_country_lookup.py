"""
The device list's countries from an offline MaxMind database: a GeoLite2
layout written here with mmdb-writer (no download, no network).
"""

import logging
from pathlib import Path

import pytest
from mmdb_writer import MMDBWriter
from netaddr import IPSet

from app.adapters.security.maxmind_ip_country_lookup_adapter import (
    MaxMindIpCountryLookupAdapter,
    country_of_record,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)


def country_database(path: Path) -> Path:
    writer = MMDBWriter(
        ip_version=6, ipv4_compatible=True, database_type="GeoLite2-Country"
    )
    writer.insert_network(
        IPSet(["31.146.0.0/16"]), {"country": {"iso_code": "GE", "names": {}}}
    )
    writer.insert_network(
        IPSet(["2a02:810::/32"]), {"country": {"iso_code": "DE", "names": {}}}
    )
    # An anycast range: only the country that registered it is known.
    writer.insert_network(
        IPSet(["45.84.0.0/16"]), {"registered_country": {"iso_code": "nl"}}
    )
    database = path / "countries.mmdb"
    writer.to_db_file(str(database))
    return database


def lookup(database: Path | None) -> MaxMindIpCountryLookupAdapter:
    environment: dict[str, str] = (
        {} if database is None else {"GEOIP_COUNTRY_DATABASE_PATH": str(database)}
    )
    return MaxMindIpCountryLookupAdapter(assemble_app_settings(environment))


def test_addresses_get_the_country_the_database_places_them_in(
    tmp_path: Path,
) -> None:
    countries = lookup(country_database(tmp_path))

    assert countries.country_of(ClientIpAddress("31.146.20.5")) == "GE"
    assert countries.country_of(ClientIpAddress("2a02:810:1::7")) == "DE"
    assert countries.country_of(ClientIpAddress("45.84.1.1")) == "NL"
    assert countries.country_of(ClientIpAddress("8.8.8.8")) is None


@pytest.mark.parametrize(
    "address",
    ["10.0.0.5", "192.168.1.1", "127.0.0.1", "::1", "fe80::1", "not an address", ""],
)
def test_private_local_and_broken_addresses_have_no_country(
    tmp_path: Path, address: str
) -> None:
    assert lookup(country_database(tmp_path)).country_of(ClientIpAddress(address)) is None


def test_without_a_database_no_address_has_a_country() -> None:
    assert lookup(None).country_of(ClientIpAddress("31.146.20.5")) is None


def test_an_unreadable_database_is_reported_once_and_ignored(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    broken = tmp_path / "broken.mmdb"
    broken.write_bytes(b"not a database")
    countries = lookup(broken)

    with caplog.at_level(logging.ERROR):
        first = countries.country_of(ClientIpAddress("31.146.20.5"))
        second = countries.country_of(ClientIpAddress("31.146.20.6"))
    reports = [record for record in caplog.records if "GEOIP" in record.getMessage()]

    assert (first, second) == (None, None)
    assert len(reports) == 1
    # The address itself never reaches the log.
    assert all("31.146" not in record.getMessage() for record in caplog.records)


def test_a_missing_database_is_no_database(tmp_path: Path) -> None:
    missing = lookup(tmp_path / "missing.mmdb")

    assert missing.country_of(ClientIpAddress("31.146.20.5")) is None


@pytest.mark.parametrize(
    "record",
    [None, "GE", {"country": "GE"}, {"country": {"iso_code": 7}}, {"country": {}}],
)
def test_records_without_a_country_code_name_none(record: object) -> None:
    assert country_of_record(record) is None


def test_a_malformed_code_names_none() -> None:
    assert country_of_record({"country": {"iso_code": "Georgia"}}) is None
