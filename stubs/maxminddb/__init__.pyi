# Typed surface of maxminddb that the device list's country lookup uses
# (app/adapters/security/maxmind_ip_country_lookup_adapter.py): its own
# annotations leave the record type and the opener's path partly unknown,
# which strict pyright refuses. A record is read as `object` and narrowed
# by the adapter.

from ipaddress import IPv4Address, IPv6Address

MODE_AUTO: int

class InvalidDatabaseError(RuntimeError): ...

class Reader:
    def get(self, ip_address: str | IPv4Address | IPv6Address) -> object: ...
    def close(self) -> None: ...

def open_database(database: str, mode: int = ...) -> Reader: ...
