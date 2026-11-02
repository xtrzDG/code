"""
Links every reply may carry whatever the business published: the
well-known map services (directions to the business) and payment services
(a deposit or an order paid where the business takes payments). An entry
is a host, matched with its subdomains, optionally with the path its
links must start with ("google.com/maps": Google's maps, not any Google
page).
"""

WELL_KNOWN_MAP_LINKS: tuple[str, ...] = (
    "maps.google.com",
    "google.com/maps",
    "maps.app.goo.gl",
    "goo.gl/maps",
    "maps.apple.com",
    "openstreetmap.org",
    "osm.org",
    "waze.com",
    "wego.here.com",
    "bing.com/maps",
    "yandex.com/maps",
    "2gis.com",
)
WELL_KNOWN_PAYMENT_LINKS: tuple[str, ...] = (
    "checkout.stripe.com",
    "buy.stripe.com",
    "billing.stripe.com",
    "paypal.com",
    "paypal.me",
    "pay.flitt.com",
    "flitt.com",
    "pay.sumup.com",
    "satispay.com",
    "revolut.me",
)
WELL_KNOWN_LINKS: tuple[str, ...] = (*WELL_KNOWN_MAP_LINKS, *WELL_KNOWN_PAYMENT_LINKS)
