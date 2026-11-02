"""
A customer's consent to marketing messages (Codice privacy art. 130, GDPR
art. 7): where it was given, how it was taken back, the wording agreed to
and what the team's card says about it.
"""

from enum import StrEnum


class MarketingConsentSource(StrEnum):
    """
    Where the customer agreed to marketing messages (the rebooking
    campaign's invitations back, recalls and pre-arrival notes):

    - BOOKING_PAGE: they ticked the unticked box on their booking's page
      (/r/{token}, the link of their written confirmation);
    - IN_PERSON: they told the team, who recorded it on their card
      (Customers → a customer), naming who recorded it.
    """

    BOOKING_PAGE = "booking_page"
    IN_PERSON = "in_person"


class MarketingConsentWithdrawal(StrEnum):
    """
    How the consent was taken back: unticked on the booking page, recorded
    by the team on the card, or the customer's STOP in a chat.
    """

    BOOKING_PAGE = "booking_page"
    IN_PERSON = "in_person"
    STOP = "stop"


class MarketingConsentText(StrEnum):
    """
    The versions of the consent wording, by the day each took effect; the
    version a customer agreed to is stored with their consent, so the exact
    text stays provable. 2026-11-02, the booking page
    (`web/src/app/r/[token]/_components/marketingConsent/consentTexts.ts`,
    15 languages) and the card's record of a consent given in person
    (`customers.consent.*` of the cabinet's dictionaries): "Send me news,
    offers and invitations to come back from {business}, in the chat this
    booking was made in. I can take this back at any time here or by
    replying STOP." A changed wording is a new value (behind a release
    gate, like every new stored value).
    """

    V2026_11_02 = "2026-11-02"


CURRENT_MARKETING_CONSENT_TEXT: MarketingConsentText = MarketingConsentText.V2026_11_02


class MarketingConsentStatus(StrEnum):
    """
    What the customer's card and booking page say (never stored): AGREED
    (recorded and not taken back), NOT_GIVEN (never recorded: every
    customer from before consent was kept), WITHDRAWN (taken back), or
    STOPPED (they said STOP, are on the suppression list or blocked: no
    marketing whatever was recorded, so the card never says "agreed").
    """

    AGREED = "agreed"
    NOT_GIVEN = "not_given"
    WITHDRAWN = "withdrawn"
    STOPPED = "stopped"
