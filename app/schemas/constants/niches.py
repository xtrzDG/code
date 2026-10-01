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


class LaunchWave(StrEnum):
    """Go-to-market priority of a niche (A first, C last)."""

    A = "a"
    B = "b"
    C = "c"


class BookableResourceKind(StrEnum):
    """What a niche books for a customer."""

    TABLE = "table"
    ROOM = "room"
    TIME_SLOT = "time_slot"
    SPECIALIST = "specialist"
    TRIAL_CLASS = "trial_class"
    VEHICLE = "vehicle"
    TOUR = "tour"
    VENUE_DATE = "venue_date"
    VIEWING = "viewing"
    SERVICE_VISIT = "service_visit"
    ORDER = "order"


class QuestionAnswerType(StrEnum):
    """Input shape of one questionnaire question."""

    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    NUMBER = "number"
    YES_NO = "yes_no"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    URL = "url"
    PHONE_NUMBER = "phone_number"


class QuestionnaireSection(StrEnum):
    """Questionnaire section a question belongs to."""

    BASICS = "basics"
    HOURS = "hours"
    OFFERING = "offering"
    BOOKING_RULES = "booking_rules"
    FAQ = "faq"
    HANDOFF = "handoff"
    CHANNELS = "channels"
