from enum import StrEnum


class DemoBusinessKey(StrEnum):
    """
    A business of the development demo data (SEED_DEMO_DATA): a Tbilisi
    restaurant and, to show that nothing is tied to one country, a Berlin
    beauty salon.
    """

    TBILISI_RESTAURANT = "tbilisi_restaurant"
    BERLIN_SALON = "berlin_salon"
