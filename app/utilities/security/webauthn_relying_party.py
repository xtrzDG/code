"""Where passkeys may be used: the relying party and the cabinet's origin."""

from urllib.parse import urlsplit

from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl

DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}


def cabinet_origin(cabinet_base_url: CabinetBaseUrl | None) -> str | None:
    """
    The origin browsers report for the cabinet (scheme, host and a port
    other than the scheme's default), which every passkey answer must
    name; None without a cabinet address.
    """

    if cabinet_base_url is None:
        return None

    parts = urlsplit(str(cabinet_base_url))
    if parts.scheme not in DEFAULT_PORTS or not parts.hostname:
        return None

    port: int | None = parts.port
    host: str = parts.hostname.lower()
    if port is None or port == DEFAULT_PORTS[parts.scheme]:
        return f"{parts.scheme}://{host}"

    return f"{parts.scheme}://{host}:{port}"
