"""The catalog of all sixteen niche templates (concept "Сценарии по нишам")."""

from app.registries.niches.templates.b2b_supply_template import (
    build_b2b_supply_template,
)
from app.registries.niches.templates.beauty_salon_template import (
    build_beauty_salon_template,
)
from app.registries.niches.templates.car_rental_and_tours_template import (
    build_car_rental_and_tours_template,
)
from app.registries.niches.templates.car_service_template import (
    build_car_service_template,
)
from app.registries.niches.templates.clinic_template import build_clinic_template
from app.registries.niches.templates.education_template import (
    build_education_template,
)
from app.registries.niches.templates.entertainment_template import (
    build_entertainment_template,
)
from app.registries.niches.templates.event_venue_template import (
    build_event_venue_template,
)
from app.registries.niches.templates.fitness_template import build_fitness_template
from app.registries.niches.templates.home_services_template import (
    build_home_services_template,
)
from app.registries.niches.templates.hotel_template import build_hotel_template
from app.registries.niches.templates.online_shop_template import (
    build_online_shop_template,
)
from app.registries.niches.templates.real_estate_template import (
    build_real_estate_template,
)
from app.registries.niches.templates.restaurant_template import (
    build_restaurant_template,
)
from app.registries.niches.templates.short_term_rental_template import (
    build_short_term_rental_template,
)
from app.registries.niches.templates.veterinary_template import (
    build_veterinary_template,
)
from app.schemas.dto.niches import NicheTemplate


def build_niche_templates() -> list[NicheTemplate]:
    """Every niche template, in the order of the concept's niche table."""

    return [
        build_restaurant_template(),
        build_hotel_template(),
        build_entertainment_template(),
        build_beauty_salon_template(),
        build_clinic_template(),
        build_fitness_template(),
        build_short_term_rental_template(),
        build_car_service_template(),
        build_car_rental_and_tours_template(),
        build_event_venue_template(),
        build_real_estate_template(),
        build_education_template(),
        build_online_shop_template(),
        build_veterinary_template(),
        build_home_services_template(),
        build_b2b_supply_template(),
    ]
