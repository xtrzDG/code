"""
WEBAUTHN_RP_ID and GEOIP_COUNTRY_DATABASE_PATH: the domain passkeys are
bound to, and the offline country database of the device list.
"""

from collections.abc import Mapping
from urllib.parse import urlsplit

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.passkeys.constrained_strings import WebAuthnRelyingPartyId
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.platform.strings import LocalFilePath
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
    parse_setting,
)

IP_ADDRESS_HOST_CHARACTERS: frozenset[str] = frozenset("0123456789.:[]")


def read_webauthn_rp_id(
    environment_variables: Mapping[str, str],
    cabinet_base_url: CabinetBaseUrl | None,
) -> WebAuthnRelyingPartyId | None:
    """
    WEBAUTHN_RP_ID, lower case: the cabinet's host or a registrable domain
    above it (browsers refuse any other). Unset: the cabinet's own host,
    unless it is an IP address (passkeys need a domain name). None without
    a cabinet address: the server offers no passkeys.

    Raises:
        ValidationFailedError: WEBAUTHN_RP_ID is not a domain name, or not
            one the cabinet's host belongs to.
    """

    host: str | None = cabinet_host(cabinet_base_url)
    raw_value: str = environment_variables.get("WEBAUTHN_RP_ID", "").strip().lower()
    if raw_value == "":
        if host is None or set(host) <= IP_ADDRESS_HOST_CHARACTERS:
            return None

        try:
            return WebAuthnRelyingPartyId(host)
        except ValueError:
            return None

    rp_id: WebAuthnRelyingPartyId = parse_setting(
        "WEBAUTHN_RP_ID", raw_value, WebAuthnRelyingPartyId
    )
    if host is not None and host != str(rp_id) and not host.endswith(f".{rp_id}"):
        raise ValidationFailedError(
            f"WEBAUTHN_RP_ID {rp_id} must be the host of CABINET_BASE_URL "
            f"({host}) or a domain it belongs to."
        )

    return rp_id


def cabinet_host(cabinet_base_url: CabinetBaseUrl | None) -> str | None:
    if cabinet_base_url is None:
        return None

    host: str | None = urlsplit(str(cabinet_base_url)).hostname
    return None if not host else host.lower()


def read_geoip_country_database_path(
    environment_variables: Mapping[str, str],
) -> LocalFilePath | None:
    """GEOIP_COUNTRY_DATABASE_PATH: a GeoLite2-Country (or compatible) .mmdb file."""

    return optional_text(
        environment_variables, "GEOIP_COUNTRY_DATABASE_PATH", LocalFilePath
    )
