# Typed surface of netaddr (it ships no py.typed): the one class the tests
# hand to mmdb-writer, a set of networks written into a test country
# database (tests/users/test_ip_country_lookup.py).

from collections.abc import Iterable

class IPSet:
    def __init__(self, iterable: Iterable[str] | None = None) -> None: ...
