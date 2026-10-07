"""Every niche's starter answers, one definition per niche."""

from app.registries.niches.starters.care_starters import (
    BEAUTY_SALON_STARTERS,
    CLINIC_STARTERS,
    VETERINARY_STARTERS,
)
from app.registries.niches.starters.hospitality_starters import (
    HOTEL_STARTERS,
    RESTAURANT_STARTERS,
    SHORT_TERM_RENTAL_STARTERS,
)
from app.registries.niches.starters.leisure_starters import (
    ENTERTAINMENT_STARTERS,
    EVENT_VENUE_STARTERS,
    FITNESS_STARTERS,
)
from app.registries.niches.starters.property_and_learning_starters import (
    EDUCATION_STARTERS,
    REAL_ESTATE_STARTERS,
)
from app.registries.niches.starters.service_starters import (
    CAR_RENTAL_AND_TOURS_STARTERS,
    CAR_SERVICE_STARTERS,
    HOME_SERVICES_STARTERS,
)
from app.registries.niches.starters.trade_starters import (
    B2B_SUPPLY_STARTERS,
    ONLINE_SHOP_STARTERS,
)
from app.schemas.dto.setup.starter_catalog import NicheStarterDefinition

NICHE_STARTERS: tuple[NicheStarterDefinition, ...] = (
    RESTAURANT_STARTERS,
    HOTEL_STARTERS,
    SHORT_TERM_RENTAL_STARTERS,
    EVENT_VENUE_STARTERS,
    ENTERTAINMENT_STARTERS,
    FITNESS_STARTERS,
    BEAUTY_SALON_STARTERS,
    CLINIC_STARTERS,
    VETERINARY_STARTERS,
    CAR_SERVICE_STARTERS,
    CAR_RENTAL_AND_TOURS_STARTERS,
    HOME_SERVICES_STARTERS,
    REAL_ESTATE_STARTERS,
    EDUCATION_STARTERS,
    ONLINE_SHOP_STARTERS,
    B2B_SUPPLY_STARTERS,
)
