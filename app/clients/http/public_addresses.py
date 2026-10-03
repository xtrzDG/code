"""
Which hosts and IP addresses the platform may connect to on someone
else's behalf: public unicast addresses only.

Refused: loopback, private (RFC 1918, unique-local IPv6), link-local
(169.254.0.0/16 with the cloud metadata services, fe80::/10), carrier-grade
NAT (100.64.0.0/10), "this network", benchmarking, documentation,
reserved, multicast and broadcast ranges, plus IPv6 forms that carry an
IPv4 address inside (IPv4-mapped, 6to4, NAT64), which are judged by that
IPv4 address. Host names that only make sense inside a network
(localhost, *.local, *.internal, ...) are refused before any lookup.
"""

import ipaddress
from typing import Final

type IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
type IpNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

BLOCKED_HOST_NAMES: Final[frozenset[str]] = frozenset(
    {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}
)
BLOCKED_HOST_SUFFIXES: Final[tuple[str, ...]] = (
    ".localhost",
    ".local",
    ".localdomain",
    ".internal",
    ".intranet",
    ".lan",
    ".home.arpa",
    ".corp",
)
# Named explicitly although most are not "global" for `ipaddress` either:
# the list documents the policy and survives library changes.
BLOCKED_NETWORKS: Final[tuple[IpNetwork, ...]] = tuple(
    ipaddress.ip_network(network)
    for network in (
        "0.0.0.0/8",  # "this network"
        "10.0.0.0/8",  # private
        "100.64.0.0/10",  # carrier-grade NAT (also Alibaba's metadata)
        "127.0.0.0/8",  # loopback
        "169.254.0.0/16",  # link-local: AWS/GCP/Azure metadata 169.254.169.254
        "172.16.0.0/12",  # private
        "192.0.0.0/24",  # IETF protocol assignments (Oracle metadata)
        "192.0.2.0/24",  # documentation
        "192.168.0.0/16",  # private
        "198.18.0.0/15",  # benchmarking
        "198.51.100.0/24",  # documentation
        "203.0.113.0/24",  # documentation
        "224.0.0.0/4",  # multicast
        "240.0.0.0/4",  # reserved and broadcast
        "::/128",  # unspecified
        "::1/128",  # loopback
        "fc00::/7",  # unique local (AWS metadata fd00:ec2::254)
        "fe80::/10",  # link-local
        "ff00::/8",  # multicast
        "2001:db8::/32",  # documentation
    )
)
NAT64_NETWORK: Final[ipaddress.IPv6Network] = ipaddress.IPv6Network("64:ff9b::/96")
ALLOWED_PORTS: Final[frozenset[int]] = frozenset({80, 443})


def is_blocked_host_name(host: str) -> bool:
    """A name that points inside a network (`host` lower-case, no trailing dot)."""

    return host in BLOCKED_HOST_NAMES or host.endswith(BLOCKED_HOST_SUFFIXES)


def parse_ip_address(text: str) -> IpAddress | None:
    """The address in `text` (an IPv6 zone is ignored), or None for a name."""

    try:
        return ipaddress.ip_address(text.split("%", 1)[0])
    except ValueError:
        return None


def is_public_address(text: str) -> bool:
    """True only for a public unicast IPv4 or IPv6 address."""

    address: IpAddress | None = parse_ip_address(text)
    if address is None:
        return False

    embedded: ipaddress.IPv4Address | None = embedded_ipv4_address(address)
    if embedded is not None:
        return is_public_ip(embedded)

    return is_public_ip(address)


def embedded_ipv4_address(address: IpAddress) -> ipaddress.IPv4Address | None:
    """The IPv4 address an IPv4-mapped, 6to4 or NAT64 IPv6 address carries."""

    if not isinstance(address, ipaddress.IPv6Address):
        return None

    if address.ipv4_mapped is not None:
        return address.ipv4_mapped

    if address.sixtofour is not None:
        return address.sixtofour

    if address in NAT64_NETWORK:
        return ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)

    return None


def is_public_ip(address: IpAddress) -> bool:
    if any(address in network for network in BLOCKED_NETWORKS):
        return False

    return address.is_global and not address.is_multicast
