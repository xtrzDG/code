"""
Hosts the link check of a reply knows by name.

- Links every reply may carry whatever the business published: the
  well-known map services (directions to the business) and the checkout
  pages of the payment services the platform takes payments with (a
  session's address a model cannot guess). An entry is a host, matched with
  its subdomains, optionally with the path its links must start with
  ("google.com/maps": Google's maps, not any Google page). A payment link
  that names a person or a shop (paypal.me/…, revolut.me/…) passes only
  when the business published it: a model that invents one could send the
  money to a stranger.
- Shared platforms, where anyone can publish a page (social networks,
  messengers, link shorteners, listings): a link the business published
  there allows that page and what is under it, never the whole platform.
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
    "pay.flitt.com",
)
WELL_KNOWN_LINKS: tuple[str, ...] = (*WELL_KNOWN_MAP_LINKS, *WELL_KNOWN_PAYMENT_LINKS)
SHARED_PLATFORM_HOSTS: tuple[str, ...] = (
    "google.com",
    "goo.gl",
    "forms.gle",
    "facebook.com",
    "fb.com",
    "fb.me",
    "instagram.com",
    "threads.net",
    "tiktok.com",
    "youtube.com",
    "youtu.be",
    "x.com",
    "twitter.com",
    "linkedin.com",
    "pinterest.com",
    "t.me",
    "telegram.me",
    "wa.me",
    "whatsapp.com",
    "viber.com",
    "m.me",
    "linktr.ee",
    "bit.ly",
    "tinyurl.com",
    "tripadvisor.com",
    "tripadvisor.it",
    "thefork.com",
    "thefork.it",
    "booking.com",
    "airbnb.com",
    "airbnb.it",
    "yelp.com",
    "paypal.com",
    "paypal.me",
    "revolut.me",
    "satispay.com",
    "sumup.com",
    "github.io",
    "wixsite.com",
    "notion.site",
    "dropbox.com",
)
