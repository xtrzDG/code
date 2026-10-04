from enum import StrEnum


class NicheKey(StrEnum):
    """Business niche with its own assistant template."""

    RESTAURANT = "restaurant"
    HOTEL = "hotel"
    ENTERTAINMENT = "entertainment"
    BEAUTY_SALON = "beauty_salon"
    CLINIC = "clinic"
    FITNESS = "fitness"
    SHORT_TERM_RENTAL = "short_term_rental"
    CAR_SERVICE = "car_service"
    CAR_RENTAL_AND_TOURS = "car_rental_and_tours"
    EVENT_VENUE = "event_venue"
    REAL_ESTATE = "real_estate"
    EDUCATION = "education"
    ONLINE_SHOP = "online_shop"
    VETERINARY = "veterinary"
    HOME_SERVICES = "home_services"
    B2B_SUPPLY = "b2b_supply"


class ExampleExchangeKind(StrEnum):
    """
    What a short example exchange of a niche shows the model.

    BOOKING_CONFIRMATION is shown only to versions that book directly;
    REQUEST_CONFIRMATION (an order or request taken with create_lead) to
    niches that take requests instead.
    """

    BOOKING_CONFIRMATION = "booking_confirmation"
    REQUEST_CONFIRMATION = "request_confirmation"
    PRICE_NOT_FOUND = "price_not_found"
    HANDOFF = "handoff"


class BookingScenarioVariant(StrEnum):
    """
    A niche's own booking autotest beyond the plain booking: booking a
    service with a master the customer names, or a room type for several
    nights. Planned as booking scenarios (kind BOOKING) from the business's
    own services and rooms.
    """

    SPECIFIC_PERFORMER = "specific_performer"
    ROOM_TYPE_STAY = "room_type_stay"


class LaunchWave(StrEnum):
    """Go-to-market priority of a niche (A first, C last)."""

    A = "a"
    B = "b"
    C = "c"


class QuestionAnswerType(StrEnum):
    """Input shape of one niche-specific profile question."""

    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    NUMBER = "number"
    YES_NO = "yes_no"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    URL = "url"
    PHONE_NUMBER = "phone_number"


class ProfileWizardStep(StrEnum):
    """The six steps of the profile wizard from the concept (section 3)."""

    NICHE_AND_LANGUAGES = "niche_and_languages"
    CONTACTS_AND_HOURS = "contacts_and_hours"
    OFFER = "offer"
    BOOKING_RULES = "booking_rules"
    FAQ_AND_HANDOFF = "faq_and_handoff"
    CHANNELS = "channels"
